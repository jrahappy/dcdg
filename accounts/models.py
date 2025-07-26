from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    website = models.URLField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'
    
    def get_absolute_url(self):
        return reverse('profile-detail', kwargs={'pk': self.pk})


class SenderInformation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='sender_info')
    business_name = models.CharField(max_length=200)
    business_address = models.TextField(blank=True)
    business_phone = models.CharField(max_length=20, blank=True)
    business_website = models.URLField(max_length=200, blank=True)
    business_logo = models.ImageField(upload_to='business_logos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.business_name} - {self.user.email}'
    
    class Meta:
        verbose_name = 'Sender Information'
        verbose_name_plural = 'Sender Information'


class SenderEmail(models.Model):
    SMTP_ENCRYPTION_CHOICES = [
        ('none', 'None'),
        ('ssl', 'SSL/TLS'),
        ('tls', 'STARTTLS'),
    ]
    
    sender_info = models.ForeignKey(SenderInformation, on_delete=models.CASCADE, related_name='sender_emails')
    email = models.EmailField()
    display_name = models.CharField(max_length=100, blank=True)
    
    # SMTP Configuration
    smtp_host = models.CharField(max_length=255, default='', help_text='SMTP server hostname (e.g., smtp.gmail.com)')
    smtp_port = models.IntegerField(default=587, help_text='SMTP server port (e.g., 587 for TLS, 465 for SSL)')
    smtp_username = models.CharField(max_length=255, default='', help_text='SMTP username (often same as email)')
    smtp_password = models.CharField(max_length=255, blank=True, help_text='SMTP password or app-specific password')
    smtp_encryption = models.CharField(max_length=10, choices=SMTP_ENCRYPTION_CHOICES, default='tls')
    
    # Status fields
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    last_verified = models.DateTimeField(null=True, blank=True)
    verification_error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.display_name} <{self.email}>' if self.display_name else self.email
    
    class Meta:
        unique_together = ['sender_info', 'email']
        ordering = ['-is_primary', '-is_verified', 'email']
