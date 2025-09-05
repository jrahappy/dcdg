from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db.models.signals import pre_save
from .models import Cart, CartItem
import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

User = get_user_model()

# Store the pre-login session key temporarily
_pre_login_session_keys = {}


@receiver(pre_save, sender=User)
def store_session_before_login(sender, instance, **kwargs):
    """Store the session key before login for cart preservation"""
    # This runs during the login process before the session is cycled
    pass  # We'll handle this differently


@receiver(user_logged_in)
def merge_cart_on_login(sender, request, user, **kwargs):
    """
    Merge anonymous cart with user cart when user logs in.
    This preserves the cart items that were added before login.
    """
    if not hasattr(request, "session"):
        return

    try:
        # Store the old session key if available (before Django cycles it)
        old_session_key = request.session.get("_old_session_key", None)
        current_session_key = request.session.session_key

        # Try to find the anonymous cart using either the old or current session key
        anonymous_cart = None

        # First, try with old session key if available
        if old_session_key:
            anonymous_cart = Cart.objects.filter(
                session_key=old_session_key,
                user__isnull=True,  # Ensure it's an anonymous cart
            ).first()
            logger.info(
                f"Looking for cart with old session key: {old_session_key[:8]}..."
            )

        # If not found and current session key is different, try with current
        if (
            not anonymous_cart
            and current_session_key
            and current_session_key != old_session_key
        ):
            anonymous_cart = Cart.objects.filter(
                session_key=current_session_key,
                user__isnull=True,  # Ensure it's an anonymous cart
            ).first()
            logger.info(
                f"Looking for cart with current session key: {current_session_key[:8] if current_session_key else 'None'}..."
            )

        # Also check for any recent anonymous carts (fallback)
        if not anonymous_cart:
            # Get the most recent anonymous cart from the last hour (reasonable timeframe)

            recent_cutoff = timezone.now() - timedelta(hours=1)
            anonymous_cart = (
                Cart.objects.filter(user__isnull=True, updated_at__gte=recent_cutoff)
                .order_by("-updated_at")
                .first()
            )
            if anonymous_cart:
                logger.info(
                    f"Found recent anonymous cart: {anonymous_cart.session_key[:8]}..."
                )

        if not anonymous_cart:
            logger.info(f"No anonymous cart found for user {user.email}")
            return

        # Check if user already has a cart
        user_cart = Cart.objects.filter(user=user).first()

        if user_cart:
            # Merge items from anonymous cart to user cart
            for anonymous_item in anonymous_cart.items.all():
                # Check if the product already exists in user's cart with same options
                existing_item = user_cart.items.filter(
                    product=anonymous_item.product,
                    selected_options=anonymous_item.selected_options,
                ).first()

                if existing_item:
                    # Update quantity if item already exists
                    existing_item.quantity += anonymous_item.quantity
                    existing_item.save()
                else:
                    # Add new item to user's cart
                    CartItem.objects.create(
                        cart=user_cart,
                        product=anonymous_item.product,
                        quantity=anonymous_item.quantity,
                        unit_price=anonymous_item.unit_price,
                        selected_options=anonymous_item.selected_options,
                    )

            # Delete the anonymous cart after merging
            anonymous_cart.delete()

            logger.info(f"Merged anonymous cart into user {user.email}'s existing cart")
        else:
            # No existing user cart, just assign the anonymous cart to the user
            anonymous_cart.user = user
            # Update the session_key to the new one
            anonymous_cart.session_key = (
                current_session_key or request.session.session_key
            )
            anonymous_cart.save()

            logger.info(f"Assigned anonymous cart to user {user.email}")

        # Clean up the old session key from session
        if "_old_session_key" in request.session:
            del request.session["_old_session_key"]
            request.session.save()

    except Exception as e:
        logger.error(f"Error merging cart for user {user.email}: {str(e)}")
        # Don't raise exception to avoid breaking login flow
