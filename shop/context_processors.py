from .models import Cart


def shop_context(request):
    """
    Context processor to add shop-related data to all templates.
    """
    context = {}
    
    # Add cart count to context
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            context['cart_item_count'] = cart.items.count()
        else:
            context['cart_item_count'] = 0
    else:
        # For anonymous users, use session-based cart
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()
            if cart:
                context['cart_item_count'] = cart.items.count()
            else:
                context['cart_item_count'] = 0
        else:
            context['cart_item_count'] = 0
    
    return context