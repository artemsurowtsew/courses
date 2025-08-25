from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from shop.models import Cart, CartItem

@receiver(user_logged_in)
def merge_session_cart_with_db_cart(sender, user, request, **kwargs):
    """
    Merge the session cart with the user's database cart upon login.
    """
    session_cart_data = request.session.get('cart')
    if session_cart_data:
        try:
            session_cart = Cart.objects.get(id=session_cart_data.get('id'), user=None)
            user_cart, created = Cart.objects.get_or_create(user=user)

            for session_item in session_cart.items.all():
                # Check if the item already exists in the user's cart
                cart_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=session_item.product,
                    defaults={'quantity': session_item.quantity}
                )
                if not created:
                    # If it exists, update the quantity
                    cart_item.quantity += session_item.quantity
                    cart_item.save()
            
            # Clear the session cart
            session_cart.delete()
            request.session['cart'] = None
        except Cart.DoesNotExist:
            pass # No session cart to merge
