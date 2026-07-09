import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.db import transaction

from apps.cart.models import CartItem
from apps.cart.services import CartService
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment, PaymentMethod
from apps.products.models import Product


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(
        cart_service: CartService,
        user: AbstractUser,
        shipping_address: str,
        payment_method: PaymentMethod | None = None,
    ) -> Order:
        """Create order, order items, and reserve stock atomically from cart"""
        cart_items = cart_service.get_items()
        if not cart_items:
            raise ValueError("Cannot create an order from an empty cart.")

        # 1. Concurrency-safe stock reservation (select_for_update)
        for item in cart_items:
            product = Product.objects.select_for_update().get(id=item["product"].id)
            if product.stock < item["quantity"]:
                raise ValueError(
                    f"Not enough stock for {product.name}. "
                    f"Available: {product.stock}, in cart: {item['quantity']}."
                )
            product.stock -= item["quantity"]
            product.save()

        # 2. Order creation
        order = Order.objects.create(
            user=user,
            status=Order.Status.PENDING,
            total_price=cart_service.get_total_price(),
            shipping_address=shipping_address,
        )

        # 3. Order Items creation
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item["product"],
                quantity=item["quantity"],
                price=item["product"].price,
            )

        # 4. Payment record creation
        Payment.objects.create(
            order=order,
            payment_method=payment_method,
            transaction_id=f"PAY-{uuid.uuid4()}",
        )

        # 5. Clear Cart
        CartItem.objects.filter(cart=cart_service.cart).delete()

        # 6. Send notifications
        OrderService.send_order_notifications(user, order)

        return order

    @staticmethod
    def adjust_stock(product: Product, quantity_change: int) -> None:
        """
        Adjust product stock.
        A positive quantity_change means reducing stock, negative returns stock.
        """
        product_to_lock = Product.objects.select_for_update().get(id=product.pk)
        if quantity_change > 0:
            if product_to_lock.stock < quantity_change:
                raise ValueError(f"Insufficient stock for {product.name}.")
            product_to_lock.stock -= quantity_change
        else:
            product_to_lock.stock += abs(quantity_change)
        product_to_lock.save()

    @staticmethod
    def recalculate_order_total(order: Order) -> Decimal:
        """Recalculate order total price from current OrderItems"""
        total = sum(item.price * item.quantity for item in order.items.all())
        order.total_price = Decimal(total)
        order.save()
        return order.total_price

    @staticmethod
    @transaction.atomic
    def update_order_item(order_item: OrderItem, old_quantity: int, new_quantity: int) -> None:
        """Adjusts the quantity of a line item and updates the product stock."""
        qty_difference = new_quantity - old_quantity
        if qty_difference != 0:
            OrderService.adjust_stock(order_item.product, qty_difference)
        order_item.quantity = new_quantity
        order_item.save()

    @staticmethod
    @transaction.atomic
    def cancel_order(order: Order) -> None:
        """
        Cancels an order, sets its status to CANCELLED,
        and returns all line item stock back to inventory.
        """
        db_order = Order.objects.select_for_update().get(pk=order.pk)
        if db_order.status == Order.Status.CANCELLED:
            return

        # Return stock
        for item in order.items.select_related("product").all():
            if item.product:
                OrderService.adjust_stock(item.product, -item.quantity)

        order.status = Order.Status.CANCELLED
        order.save()

    @staticmethod
    def send_order_notifications(user: AbstractUser, order: Order) -> None:
        """Send email notifications to the user and admin about the new order."""
        try:
            send_mail(
                subject=f"Order Confirmation - Order #{order.pk}",
                message=(
                    f"Hello {user.username or 'Customer'},\n\n"
                    f"Thank you for your order!\n\n"
                    f"Order Details:\n"
                    f"Order ID: #{order.pk}\n"
                    f"Total: ${order.total_price}\n"
                    f"Shipping Address:\n{order.shipping_address}\n\n"
                    f"We will process your order soon."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )

            User = get_user_model()
            admin_emails = list(User.objects.filter(is_staff=True).values_list("email", flat=True))
            if not admin_emails:
                admin_emails = ["admin@example.com"]

            send_mail(
                subject=f"New Order Placed - Order #{order.pk}",
                message=(
                    f"A new order #{order.pk} has been placed by user: {user.username}.\n"
                    f"Total: ${order.total_price}\n"
                    f"Shipping Address:\n{order.shipping_address}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=True,
            )
        except Exception as mail_err:
            print(f"Failed to send checkout email notifications: {mail_err}")
