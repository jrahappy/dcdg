from django.db import models
from django.contrib.auth import get_user_model
from customer.models import Customer
from django.utils import timezone

User = get_user_model()


class TargetGroup(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    customers = models.ManyToManyField(Customer, related_name='target_groups')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='target_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.customers.count()} customers)"
    
    @property
    def customer_count(self):
        return self.customers.count()
    
    @property
    def campaign_count(self):
        return self.campaigns.count()


class EmailCampaign(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=500)
    content = models.TextField()
    from_email = models.EmailField(blank=True)  # If blank, use default
    target_group = models.ForeignKey(TargetGroup, on_delete=models.PROTECT, related_name='campaigns')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    sent_time = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistics
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"
    
    def mark_as_sent(self):
        self.status = 'sent'
        self.sent_time = timezone.now()
        self.save()


class EmailLog(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, related_name='email_logs')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='email_logs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['campaign', 'customer']
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.campaign.name} to {self.customer.email} - {self.get_status_display()}"
