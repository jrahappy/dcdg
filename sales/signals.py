from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Payment


@receiver(post_save, sender=Payment)
def payment_saved_handler(sender, instance, created, **kwargs):
    """
    Signal handler that recalculates invoice paid_amount when a Payment is created or updated.
    This ensures the invoice's paid_amount always reflects the actual total of completed payments.
    """
    if instance.invoice:
        # Recalculate the paid amount for the associated invoice
        instance.invoice.recalculate_paid_amount()


@receiver(post_delete, sender=Payment)
def payment_deleted_handler(sender, instance, **kwargs):
    """
    Signal handler that recalculates invoice paid_amount when a Payment is deleted.
    This ensures the invoice's paid_amount is updated when payments are removed.
    """
    if instance.invoice:
        # Recalculate the paid amount for the associated invoice
        instance.invoice.recalculate_paid_amount()