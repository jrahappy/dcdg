from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from django.urls import reverse
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout
from .models import Profile
from .forms import ProfileUpdateForm, UserUpdateForm


class EmailConfirmationRedirectView(View):
    """Redirect email confirmation attempts since we have it disabled"""
    def get(self, request, *args, **kwargs):
        messages.info(request, "Email verification is not required. You can proceed to use your account.")
        if request.user.is_authenticated:
            return redirect('profile')
        return redirect('account_login')
    
    def post(self, request, *args, **kwargs):
        # Handle POST requests same as GET
        return self.get(request, *args, **kwargs)


def redirect_email_confirm(request, *args, **kwargs):
    """Catch-all redirect for any email confirmation URLs"""
    messages.info(request, "Email verification is not required for this site.")
    if request.user.is_authenticated:
        return redirect('profile')
    return redirect('account_login')


@login_required
def profile_view(request):
    """Display user profile"""
    # Ensure profile exists
    if not hasattr(request.user, 'profile'):
        Profile.objects.create(user=request.user)
    
    context = {
        'user': request.user,
        'profile': request.user.profile
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def account_profile(request):
    """Account management - Profile section"""
    if not hasattr(request.user, 'profile'):
        Profile.objects.create(user=request.user)
    
    context = {
        'user': request.user,
        'profile': request.user.profile
    }
    return render(request, 'accounts/account_profile.html', context)


@login_required
def account_info(request):
    """Account management - User Information section"""
    if not hasattr(request.user, 'profile'):
        Profile.objects.create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your information has been updated!')
            return redirect('account-info')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'accounts/account_info.html', context)


@login_required
def account_security(request):
    """Account management - Security section"""
    password_form = None
    
    # Handle password change
    if request.method == 'POST' and 'change_password' in request.POST:
        password_form = PasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('account-security')
    else:
        password_form = PasswordChangeForm(request.user)
    
    context = {
        'user': request.user,
        'last_login': request.user.last_login,
        'date_joined': request.user.date_joined,
        'password_form': password_form,
    }
    return render(request, 'accounts/account_security.html', context)


@login_required
def profile_edit(request):
    """Edit user profile"""
    # Ensure profile exists
    if not hasattr(request.user, 'profile'):
        Profile.objects.create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'accounts/profile_edit.html', context)


@login_required
def logout_confirm(request):
    """Display logout confirmation page"""
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return redirect('landing:home')
    
    # Clear any existing messages to prevent confusion
    storage = messages.get_messages(request)
    for _ in storage:
        pass  # This clears the messages
    
    return render(request, 'accounts/logout_confirm.html')