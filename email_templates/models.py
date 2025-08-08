from django.db import models
from django.conf import settings
from accounts.models import SenderEmail


class EmailTemplate(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('plain', 'Plain Text'),
        ('html', 'HTML'),
        ('both', 'Both HTML and Plain Text'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200, help_text="Template name for internal reference")
    subject = models.CharField(max_length=500, help_text="Email subject line")
    
    # Sender Information
    sender_email = models.ForeignKey(
        SenderEmail, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Select the sender email address"
    )
    sender_name = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Optional: Override sender name for this template"
    )
    
    # Content
    content_type = models.CharField(
        max_length=10, 
        choices=CONTENT_TYPE_CHOICES, 
        default='both',
        help_text="Email content format"
    )
    html_content = models.TextField(
        blank=True,
        help_text="HTML version of the email content"
    )
    plain_content = models.TextField(
        blank=True,
        help_text="Plain text version of the email content"
    )
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='email_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Template Variables
    available_variables = models.JSONField(
        default=dict,
        blank=True,
        help_text="Available template variables and their descriptions"
    )
    
    # Settings
    track_opens = models.BooleanField(default=True, help_text="Track email opens")
    track_clicks = models.BooleanField(default=True, help_text="Track link clicks")
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['status', '-updated_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_sender_display(self):
        """Get formatted sender display"""
        if self.sender_name and self.sender_email:
            return f"{self.sender_name} <{self.sender_email.email}>"
        elif self.sender_email:
            return self.sender_email.email
        return "No sender selected"
    
    def has_html_content(self):
        return self.content_type in ['html', 'both'] and self.html_content
    
    def has_plain_content(self):
        return self.content_type in ['plain', 'both'] and self.plain_content
    
    def get_default_variables(self):
        """Return default template variables"""
        return {
            'first_name': 'Recipient first name',
            'last_name': 'Recipient last name',
            'email': 'Recipient email address',
            'company_name': 'Recipient company name',
            'unsubscribe_link': 'Unsubscribe link',
            'target_link': 'Target/Campaign specific link',
            'current_year': 'Current year',
            'current_date': 'Current date',
        }


class EmailTemplateVariables(models.Model):
    VARIABLE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('url', 'URL'),
        ('email', 'Email'),
        ('boolean', 'Boolean'),
        ('choice', 'Choice'),
    ]
    
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.CASCADE,
        related_name='variables'
    )
    name = models.CharField(
        max_length=100,
        help_text="Variable name (e.g., 'customer_name', 'discount_code')"
    )
    type = models.CharField(
        max_length=20,
        choices=VARIABLE_TYPE_CHOICES,
        default='text',
        help_text="Variable data type"
    )
    length = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum length for text/url/email types"
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Description of what this variable represents"
    )
    default_value = models.CharField(
        max_length=500,
        blank=True,
        help_text="Default value if not provided"
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether this variable must be provided"
    )
    choices = models.JSONField(
        default=list,
        blank=True,
        help_text="Available choices for 'choice' type variables"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['template', 'name']
        indexes = [
            models.Index(fields=['template', 'name']),
        ]
    
    def __str__(self):
        return f"{self.template.title} - {self.name}"
    
    def get_variable_tag(self):
        """Return the variable tag to use in templates"""
        return f"{{{{{self.name}}}}}"
    
    def validate_value(self, value):
        """Validate a value against this variable's constraints"""
        if self.is_required and not value:
            return False, "This variable is required"
        
        if not value:
            return True, None
        
        if self.type == 'text' and self.length and len(str(value)) > self.length:
            return False, f"Value exceeds maximum length of {self.length}"
        
        if self.type == 'number':
            try:
                float(value)
            except ValueError:
                return False, "Value must be a number"
        
        if self.type == 'email':
            # Basic email validation
            if '@' not in str(value):
                return False, "Invalid email format"
        
        if self.type == 'choice' and self.choices:
            if value not in self.choices:
                return False, f"Value must be one of: {', '.join(self.choices)}"
        
        return True, None