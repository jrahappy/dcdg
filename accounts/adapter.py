from allauth.account.adapter import DefaultAccountAdapter
from django.shortcuts import redirect
from django.urls import reverse


class NoEmailVerificationAdapter(DefaultAccountAdapter):
    def is_email_verification_mandatory(self, request, email_address):
        """Override to always return False since we disabled email verification"""
        return False
    
    def respond_email_verification_sent(self, request, email_address):
        """Override to redirect to profile instead of showing email verification sent page"""
        return redirect(reverse('profile'))
    
    def get_email_confirmation_url(self, request, emailconfirmation):
        """Override to redirect to profile instead of email confirmation"""
        return reverse('profile')
    
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """Override to not send any email"""
        pass
    
    def get_login_redirect_url(self, request):
        """
        Returns the URL to redirect to after a successful login
        based on the user's role.
        """
        user = request.user
        
        if user.is_authenticated:
            # Check if user is a factory user
            try:
                from factory.models import FactoryUser
                factory_user = user.factory_profile
                if factory_user and factory_user.is_active:
                    return reverse('factory_portal:dashboard')
            except (FactoryUser.DoesNotExist, AttributeError):
                pass
            
            # Check if user is a customer (shop user)
            try:
                from customer.models import Customer
                customer = user.customer
                if customer:
                    return reverse('customer_portal:dashboard')
            except (Customer.DoesNotExist, AttributeError):
                pass
            
            # Check if user is staff/admin
            if user.is_staff or user.is_superuser:
                return reverse('dashboard:home')
        
        # Default redirect (fallback to shop)
        return '/shop/'