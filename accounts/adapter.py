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