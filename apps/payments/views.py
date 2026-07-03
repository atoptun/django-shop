import json
import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.orders.models import Order
from apps.payments.forms import (
    BankTransferPaymentForm,
    CardPaymentForm,
    CashOnDeliveryForm,
    PayPalPaymentForm,
    get_payment_form_class,
)
from apps.payments.models import Payment, PaymentMethod
from apps.payments.providers import PaymentProviderNotFound
from apps.payments.services import PaymentService


class PaymentProcessingView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest, order_uuid: uuid.UUID) -> HttpResponse:
        order = get_object_or_404(Order, uuid=order_uuid, user=request.user)
        payment = get_object_or_404(Payment, order=order)

        if payment.status == Payment.Status.COMPLETED:
            messages.info(request, "This order has already been paid.")
            return redirect("accounts:order_history")

        payment_methods = PaymentMethod.objects.filter(is_active=True)
        selected_method = payment.payment_method or payment_methods.first()

        forms_map = {
            "debit": CardPaymentForm(),
            "wallet": PayPalPaymentForm(),
            "bank": BankTransferPaymentForm(),
            "cod": CashOnDeliveryForm(),
        }

        return render(
            request,
            "payments/pay.html",
            {
                "order": order,
                "payment": payment,
                "payment_methods": payment_methods,
                "selected_method": selected_method,
                "forms": forms_map,
            },
        )

    def post(self, request: HttpRequest, order_uuid: uuid.UUID) -> HttpResponse:
        order = get_object_or_404(Order, uuid=order_uuid, user=request.user)
        payment = get_object_or_404(Payment, order=order)

        method_id = request.POST.get("payment_method")
        try:
            payment_method = PaymentMethod.objects.get(id=method_id, is_active=True)
            payment.payment_method = payment_method
            payment.save()
        except (PaymentMethod.DoesNotExist, ValueError):
            messages.error(request, "Invalid payment method selected.")
            return redirect("payments:pay", order_uuid=order.uuid)

        form_class = get_payment_form_class(payment_method.code)
        form = form_class(request.POST)

        if not form.is_valid():
            messages.error(request, "Invalid payment details provided.")
            payment_methods = PaymentMethod.objects.filter(is_active=True)

            forms_map = {
                "debit": CardPaymentForm(),
                "wallet": PayPalPaymentForm(),
                "bank": BankTransferPaymentForm(),
                "cod": CashOnDeliveryForm(),
            }
            forms_map[payment_method.code.lower()] = form

            return render(
                request,
                "payments/pay.html",
                {
                    "order": order,
                    "payment": payment,
                    "payment_methods": payment_methods,
                    "selected_method": payment_method,
                    "forms": forms_map,
                    "error": "Please correct the errors in the payment form.",
                },
            )

        data = form.cleaned_data
        try:
            result = PaymentService.process_order_payment(order, payment_method, data)
        except PaymentProviderNotFound as e:
            messages.error(request, f"Configuration Error: {e}")
            payment_methods = PaymentMethod.objects.filter(is_active=True)
            forms_map = {
                "debit": CardPaymentForm(),
                "wallet": PayPalPaymentForm(),
                "bank": BankTransferPaymentForm(),
                "cod": CashOnDeliveryForm(),
            }
            return render(
                request,
                "payments/pay.html",
                {
                    "order": order,
                    "payment": payment,
                    "payment_methods": payment_methods,
                    "selected_method": payment_method,
                    "forms": forms_map,
                    "error": str(e),
                },
            )

        if result["success"]:
            if result["status"] == Payment.Status.COMPLETED:
                messages.success(request, f"Payment for Order #{order.uuid} was successful!")
            elif result["status"] == Payment.Status.PROCESSING:
                messages.info(
                    request,
                    f"Payment for Order #{order.uuid} is being processed "
                    "(Bank Transfer). Waiting for verification.",
                )
            elif result["status"] == Payment.Status.PENDING:
                messages.success(
                    request,
                    f"Order #{order.uuid} placed successfully via "
                    "Cash On Delivery! Pay on arrival.",
                )
            return redirect("accounts:order_history")
        else:
            messages.error(request, f"Payment Failed: {result['error']}")
            payment_methods = PaymentMethod.objects.filter(is_active=True)

            forms_map = {
                "debit": CardPaymentForm(),
                "wallet": PayPalPaymentForm(),
                "bank": BankTransferPaymentForm(),
                "cod": CashOnDeliveryForm(),
            }
            forms_map[payment_method.code.lower()] = form

            return render(
                request,
                "payments/pay.html",
                {
                    "order": order,
                    "payment": payment,
                    "payment_methods": payment_methods,
                    "selected_method": payment_method,
                    "forms": forms_map,
                    "error": result["error"],
                },
            )


@method_decorator(csrf_exempt, name="dispatch")
class PaymentWebhookView(View):
    """Webhook simulation endpoint supporting provider subroutes."""

    def post(self, request: HttpRequest, provider_name: str) -> JsonResponse:
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        try:
            result = PaymentService.process_webhook_payment(provider_name, payload)
            if result["success"]:
                return JsonResponse({"status": f"{provider_name} payment completed"})
            return JsonResponse(
                {"error": result.get("error", "Webhook processing failed")}, status=400
            )
        except PaymentProviderNotFound as e:
            return JsonResponse({"error": str(e)}, status=400)
        except Payment.DoesNotExist:
            return JsonResponse({"error": "Payment not found"}, status=404)
