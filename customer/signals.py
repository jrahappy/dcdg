from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Customer, Organization

User = get_user_model()


@receiver(post_save, sender=User)
def create_customer_for_user(sender, instance, created, **kwargs):
    """
    Automatically create a Customer record when a new User is created.
    This is especially useful for users who sign up through the shop.
    
    Organizations are only for admin/staff internal use, so regular
    customers are NOT automatically assigned to organizations.
    """
    if created:
        # Check if customer already exists (in case of manual creation)
        if not hasattr(instance, 'customer'):
            # Only assign organization if user is staff/admin
            organization = None
            role = 'customer'
            
            # If this is a staff member, admin can manually assign them to an organization later
            # Regular customers should never have an organization
            
            Customer.objects.create(
                user=instance,
                email=instance.email,
                first_name=instance.first_name or '',
                last_name=instance.last_name or '',
                company_category='customer',  # Default to customer type
                organization=organization,  # Always None for regular customers
                role=role,
                is_active=True
            )


@receiver(post_save, sender=User)
def save_customer_profile(sender, instance, **kwargs):
    """
    Save the customer profile when the user is saved (if it exists).
    """
    if hasattr(instance, 'customer'):
        # Update email if changed on user
        if instance.customer.email != instance.email:
            instance.customer.email = instance.email
            instance.customer.save()