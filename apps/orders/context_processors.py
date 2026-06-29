from .services import CartService


def cart_count(request):
    """
    Context processor to add the total cart count to all template contexts.
    """
    # Avoid running for admin page requests to avoid performance overhead
    if request.path.startswith("/admin/"):
        return {}

    cart_service = CartService(request)
    return {"cart_count": cart_service.get_total_items()}
