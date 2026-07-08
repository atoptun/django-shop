from decimal import Decimal
from typing import Any

from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.http import HttpRequest

from apps.cart.models import Cart, CartItem
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
            self.cart, _ = Cart.objects.get_or_create(user=self.user)
        else:
            self.cart = None
            if "cart" not in self.request.session:
                self.request.session["cart"] = {}
            self.session_cart = self.request.session["cart"]

    def add(self, product_id: int, quantity: int = 1) -> int:
        """Add a product to the cart or update its quantity."""

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
            self.session_cart[product_id_str] = new_qty
            self.request.session.modified = True
            return new_qty

    def update(self, product_id: int, quantity: int) -> int:
        """Update the quantity of a product in the cart. If quantity is 0, remove the item."""

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
        """Remove a product from the cart."""

        product_id_str = str(product_id)
        if self.user and self.user.is_authenticated:
            CartItem.objects.filter(cart=self.cart, product_id=product_id).delete()
        else:
            if product_id_str in self.session_cart:
                del self.session_cart[product_id_str]
                self.request.session.modified = True

    def get_product_quantity(self, product_id: int) -> int:
        """Get the quantity of a specific product in the cart."""

        product_id_str = str(product_id)
        if self.user and self.user.is_authenticated:
            try:
                return CartItem.objects.get(cart=self.cart, product_id=product_id).quantity
            except CartItem.DoesNotExist:
                return 0
        else:
            return self.session_cart.get(product_id_str, 0)

    def get_total_items(self) -> int:
        """Get the total number of items in the cart."""

        if self.user and self.user.is_authenticated:
            return sum(item.quantity for item in self.cart.items.all())  # type: ignore
        else:
            return sum(self.session_cart.values())

    def get_items(self) -> list[dict[str, Any]]:
        """
        Returns a list of dicts:
        [{'product': product, 'quantity': quantity, 'subtotal': subtotal}]
        """
        items: list[dict[str, Any]] = []
        if self.user and self.user.is_authenticated:
            for item in self.cart.items.select_related("product").all():  # type: ignore
                items.append(
                    {
                        "product": item.product,
                        "quantity": item.quantity,
                        "subtotal": item.subtotal,
                    }
                )
        else:
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
                        }
                    )
        return items

    def get_total_price(self) -> Decimal:
        """Get the total price of all items in the cart."""

        return sum((item["subtotal"] for item in self.get_items()), Decimal(0))

    def merge_session_cart(self) -> None:
        """
        Merges session cart into DB cart upon login.
        """
        if not self.user.is_authenticated:  # type: ignore
            return
        session_cart: dict[str, int] = self.request.session.get("cart", {})
        if not session_cart:
            return

        product_ids = [int(k) for k in session_cart]
        products = {p.pk: p for p in Product.objects.filter(id__in=product_ids)}

        for pid_str, qty in session_cart.items():
            pid = int(pid_str)
            product = products.get(pid)
            if product is None:
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
        self.request.session["cart"] = {}
        self.request.session.modified = True
