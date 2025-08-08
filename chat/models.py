from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ChatRoom(models.Model):
    """A chat room between a customer and shop manager"""
    ROOM_STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('archived', 'Archived'),
    ]
    
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='customer_chats',
        help_text="The customer initiating the chat"
    )
    manager = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='manager_chats',
        help_text="The shop manager handling the chat"
    )
    subject = models.CharField(
        max_length=200, 
        help_text="Brief subject of the chat"
    )
    status = models.CharField(
        max_length=20, 
        choices=ROOM_STATUS_CHOICES, 
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Chat Room'
        verbose_name_plural = 'Chat Rooms'
    
    def __str__(self):
        return f"Chat: {self.subject} - {self.customer.get_full_name()}"
    
    @property
    def unread_count_for_customer(self):
        """Count of unread messages for the customer"""
        return self.messages.filter(sender=self.manager, is_read=False).count()
    
    @property
    def unread_count_for_manager(self):
        """Count of unread messages for the manager"""
        return self.messages.filter(sender=self.customer, is_read=False).count()
    
    @property
    def last_message(self):
        """Get the last message in the chat"""
        return self.messages.order_by('-created_at').first()


class ChatMessage(models.Model):
    """Individual messages within a chat room"""
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text Message'),
        ('image', 'Image'),
        ('file', 'File Attachment'),
        ('system', 'System Message'),
    ]
    
    chat_room = models.ForeignKey(
        ChatRoom, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='sent_messages'
    )
    message_type = models.CharField(
        max_length=20, 
        choices=MESSAGE_TYPE_CHOICES, 
        default='text'
    )
    content = models.TextField()
    attachment = models.FileField(
        upload_to='chat_attachments/%Y/%m/', 
        null=True, 
        blank=True,
        help_text="For image or file messages"
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'
    
    def __str__(self):
        sender_name = self.sender.get_full_name() if self.sender else "System"
        return f"{sender_name}: {self.content[:50]}..."
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def save(self, *args, **kwargs):
        """Update chat room's updated_at when a new message is added"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.chat_room.save(update_fields=['updated_at'])


class ChatNotification(models.Model):
    """Notifications for new messages"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='chat_notifications'
    )
    chat_room = models.ForeignKey(
        ChatRoom, 
        on_delete=models.CASCADE
    )
    message = models.ForeignKey(
        ChatMessage, 
        on_delete=models.CASCADE
    )
    is_seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Chat Notification'
        verbose_name_plural = 'Chat Notifications'
    
    def __str__(self):
        return f"Notification for {self.user.get_full_name()}"