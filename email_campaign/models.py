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
    
    CAMPAIGN_TYPE_CHOICES = [
        ('marketing', 'Marketing Campaign'),
        ('periodic', 'Periodic Campaign'),
    ]
    
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=500, blank=True)  # Can be overridden from template
    content = models.TextField(blank=True)  # Legacy field, will be deprecated
    email_template = models.ForeignKey('email_templates.EmailTemplate', on_delete=models.PROTECT, related_name='marketing_campaigns', null=True, blank=True)
    from_email = models.EmailField(blank=True)  # If blank, use default
    target_group = models.ForeignKey(TargetGroup, on_delete=models.PROTECT, related_name='campaigns')
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPE_CHOICES, default='marketing')
    
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


class PeriodicCampaign(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ]
    
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_group = models.ForeignKey(TargetGroup, on_delete=models.PROTECT, related_name='periodic_campaigns')
    email_template = models.ForeignKey('email_templates.EmailTemplate', on_delete=models.PROTECT, related_name='periodic_campaigns')
    
    # Target link configuration
    target_link = models.URLField(max_length=500, help_text="Base URL for the campaign")
    target_link_parameter = models.CharField(
        max_length=200, 
        blank=True,
        help_text="URL parameters to append (e.g., ?utm_source=email&utm_campaign=periodic)"
    )
    
    # Schedule configuration
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='weekly')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_run = models.DateTimeField()
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='periodic_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistics
    total_sent = models.IntegerField(default=0)
    last_run = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
    
    def get_full_target_link(self):
        """Get the complete target link with parameters"""
        if self.target_link_parameter:
            separator = '&' if '?' in self.target_link else '?'
            return f"{self.target_link}{separator}{self.target_link_parameter}"
        return self.target_link


class PeriodicCampaignLog(models.Model):
    """Log entry for each periodic campaign execution"""
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    periodic_campaign = models.ForeignKey(PeriodicCampaign, on_delete=models.CASCADE, related_name='logs')
    
    # Execution details
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    
    # Email details
    recipients_count = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    
    # Link to the actual campaign that was created
    email_campaign = models.ForeignKey(EmailCampaign, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.periodic_campaign.name} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
