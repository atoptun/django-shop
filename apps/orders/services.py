from apps.orders.models import Cart, CartItem
from apps.products.models import Product


class CartService:
    def __init__(self, request, user=None):
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

    def add(self, product_id, quantity=1):
        product_id_str = str(product_id)
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

    def update(self, product_id, quantity):
        product_id_str = str(product_id)
        if self.user and self.user.is_authenticated:
            if quantity <= 0:
                CartItem.objects.filter(cart=self.cart, product_id=product_id).delete()
                return 0
            else:
                item, _ = CartItem.objects.get_or_create(cart=self.cart, product_id=product_id)
                item.quantity = quantity
                item.save()
                return item.quantity
        else:
            if quantity <= 0:
                if product_id_str in self.session_cart:
                    del self.session_cart[product_id_str]
                self.request.session.modified = True
                return 0
            else:
                self.session_cart[product_id_str] = quantity
                self.request.session.modified = True
                return quantity

    def remove(self, product_id):
        product_id_str = str(product_id)
        if self.user and self.user.is_authenticated:
            CartItem.objects.filter(cart=self.cart, product_id=product_id).delete()
        else:
            if product_id_str in self.session_cart:
                del self.session_cart[product_id_str]
                self.request.session.modified = True

    def get_product_quantity(self, product_id):
        product_id_str = str(product_id)
        if self.user and self.user.is_authenticated:
            try:
                return CartItem.objects.get(cart=self.cart, product_id=product_id).quantity
            except CartItem.DoesNotExist:
                return 0
        else:
            return self.session_cart.get(product_id_str, 0)

    def get_total_items(self):
        if self.user and self.user.is_authenticated:
            return sum(item.quantity for item in self.cart.items.all())
        else:
            return sum(self.session_cart.values())

    def get_items(self):
        """
        Returns a list of dicts:
        [{'product': product, 'quantity': quantity, 'subtotal': subtotal, 'total_price': subtotal}]
        """
        items = []
        if self.user and self.user.is_authenticated:
            for item in self.cart.items.select_related("product").all():
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
            product_ids = [int(pid) for pid in self.session_cart.keys()]
            products = {p.pk: p for p in Product.objects.filter(id__in=product_ids)}
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

    def get_total_price(self):
        return sum(item["subtotal"] for item in self.get_items())

    def merge_session_cart(self):
        """
        Merges session cart into DB cart upon login.
        """
        if not self.user.is_authenticated:
            return
        session_cart = self.request.session.get("cart", {})
        if not session_cart:
            return
        for pid_str, qty in session_cart.items():
            pid = int(pid_str)
            item, created = CartItem.objects.get_or_create(cart=self.cart, product_id=pid)
            if created:
                item.quantity = qty
            else:
                item.quantity += qty
            item.save()
        # Clear session cart after merging
        self.request.session["cart"] = {}
        self.request.session.modified = True
