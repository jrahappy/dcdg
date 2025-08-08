from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

# All models are imported from the customer app
# This file is kept for potential future customer portal specific models

User = get_user_model()


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('order', 'Order Update'),
        ('shipping', 'Shipping Update'),
        ('promotion', 'Promotion'),
        ('system', 'System Message'),
        ('account', 'Account Update'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    link = models.URLField(blank=True, help_text='Optional link for the notification')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.get_full_name()}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])