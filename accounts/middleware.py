from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class EmailVerificationRedirectMiddleware:
    """Middleware to redirect email verification URLs since we have it disabled"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if the path contains email confirmation/verification URLs
        if 'confirm-email' in request.path or 'verification-sent' in request.path:
            messages.info(request, "Email verification is not required. You can proceed to use your account.")
            if request.user.is_authenticated:
                return redirect(reverse('profile'))
            else:
                return redirect(reverse('account_login'))
        
        response = self.get_response(request)
        return response