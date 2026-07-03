import uuid
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpRequest

from apps.orders.models import Cart, CartItem, Order, OrderItem
from apps.payments.models import Payment, PaymentMethod
from apps.products.models import Product


class CartService:
    request: HttpRequest
    user: AbstractUser | AnonymousUser | None
    cart: Cart | None
    session_cart: dict[str, int]

    def __init__(
        self, request: HttpRequest, user: AbstractUser | AnonymousUser | None = None
    ) -> None:
        self.request = request
        self.user = user or getattr(request, "user", None)
        if self.user and self.user.is_authenticated:
            # Get or create DB cart
            self.cart, _ = Cart.objects.get_or_create(user=self.user)
        else:
            self.cart = None
            if "cart" not in self.request.session:
                self.request.session["cart"] = {}
            self.session_cart = self.request.session["cart"]

    def add(self, product_id: int, quantity: int = 1) -> int:
        product_id_str = str(product_id)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist as e:
            raise ValueError("Product does not exist") from e

        current_qty = self.get_product_quantity(product_id)
        new_qty = current_qty + quantity

        if new_qty > product.stock:
            raise ValueError(f"Only {product.stock} items are available in stock.")

        if self.user and self.user.is_authenticated:
            item, created = CartItem.objects.get_or_create(cart=self.cart, product_id=product_id)
            if not created:
                item.quantity += quantity
            else:
                item.quantity = quantity
            item.save()
            return item.quantity
        else:
            current_qty = self.session_cart.get(product_id_str, 0)
            new_qty = current_qty + quantity
            self.session_cart[product_id_str] = new_qty
            self.request.session.modified = True
            return new_qty

    def update(self, product_id: int, quantity: int) -> int:
        product_id_str = str(product_id)
        if quantity <= 0:
            if self.user and self.user.is_authenticated:
                CartItem.objects.filter(cart=self.cart, product_id=product_id).delete()
                return 0
            else:
                if product_id_str in self.session_cart:
                    del self.session_cart[product_id_str]
                self.request.session.modified = True
                return 0

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist as e:
            raise ValueError("Product does not exist") from e

        if quantity > product.stock:
            raise ValueError(f"Only {product.stock} items are available in stock.")

        if self.user and self.user.is_authenticated:
            item, _ = CartItem.objects.get_or_create(cart=self.cart, product_id=product_id)
            item.quantity = quantity
            item.save()
            return item.quantity
        else:
            self.session_cart[product_id_str] = quantity
            self.request.session.modified = True
            return quantity

    def remove(self, product_id: int) -> None:
        product_id_str = str(product_id)
        if self.user and self.user.is_authenticated:
            CartItem.objects.filter(cart=self.cart, product_id=product_id).delete()
        else:
            if product_id_str in self.session_cart:
                del self.session_cart[product_id_str]
                self.request.session.modified = True

    def get_product_quantity(self, product_id: int) -> int:
        product_id_str = str(product_id)
        if self.user and self.user.is_authenticated:
            try:
                return CartItem.objects.get(cart=self.cart, product_id=product_id).quantity
            except CartItem.DoesNotExist:
                return 0
        else:
            return self.session_cart.get(product_id_str, 0)

    def get_total_items(self) -> int:
        if self.user and self.user.is_authenticated:
            return sum(item.quantity for item in self.cart.items.all())  # type: ignore
        else:
            return sum(self.session_cart.values())

    def get_items(self) -> list[dict[str, Any]]:
        """
        Returns a list of dicts:
        [{'product': product, 'quantity': quantity, 'subtotal': subtotal, 'total_price': subtotal}]
        """
        items: list[dict[str, Any]] = []
        if self.user and self.user.is_authenticated:
            for item in self.cart.items.select_related("product").all():  # type: ignore
                items.append(
                    {
                        "product": item.product,
                        "quantity": item.quantity,
                        "subtotal": item.subtotal,
                        "total_price": item.subtotal,
                    }
                )
        else:
            # Bulk fetch products in the session cart to avoid N+1 queries
            product_ids: list[int] = [int(pid) for pid in self.session_cart.keys()]
            products: dict[int, Product] = {
                p.pk: p for p in Product.objects.filter(id__in=product_ids)
            }
            for pid_str, qty in self.session_cart.items():
                pid = int(pid_str)
                if pid in products:
                    product = products[pid]
                    items.append(
                        {
                            "product": product,
                            "quantity": qty,
                            "subtotal": product.price * qty,
                            "total_price": product.price * qty,
                        }
                    )
        return items

    def get_total_price(self) -> Decimal | float:
        return sum(item["subtotal"] for item in self.get_items())

    def merge_session_cart(self) -> None:
        """
        Merges session cart into DB cart upon login.
        """
        if not self.user.is_authenticated:  # type: ignore
            return
        session_cart: dict[str, int] = self.request.session.get("cart", {})
        if not session_cart:
            return
        for pid_str, qty in session_cart.items():
            pid = int(pid_str)
            try:
                product = Product.objects.get(id=pid)
            except Product.DoesNotExist:
                continue

            item, created = CartItem.objects.get_or_create(cart=self.cart, product_id=pid)
            if created:
                item.quantity = min(qty, product.stock)
            else:
                item.quantity = min(item.quantity + qty, product.stock)

            if item.quantity <= 0:
                item.delete()
            else:
                item.save()
        # Clear session cart after merging
        self.request.session["cart"] = {}
        self.request.session.modified = True


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
        db_order = Order.objects.get(pk=order.pk)
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
