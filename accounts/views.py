from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from django.urls import reverse
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout
from django.http import JsonResponse
from django.utils import timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .models import Profile, SenderInformation, SenderEmail
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


def test_smtp_connection(smtp_host, smtp_port, smtp_username, smtp_password, smtp_encryption, test_email):
    """Test SMTP connection and return success/error message"""
    try:
        # Create SMTP connection based on encryption type
        if smtp_encryption == 'ssl':
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            if smtp_encryption == 'tls':
                server.starttls()
        
        # Login
        server.login(smtp_username, smtp_password)
        
        # Send test email
        msg = MIMEMultipart()
        msg['From'] = test_email
        msg['To'] = test_email
        msg['Subject'] = 'SMTP Configuration Test'
        
        body = """This is a test email to verify your SMTP configuration.
        
If you received this email, your SMTP settings are configured correctly!
        
Best regards,
Your Dental Support System"""
        
        msg.attach(MIMEText(body, 'plain'))
        server.send_message(msg)
        server.quit()
        
        return True, "SMTP connection successful! Test email sent."
    except Exception as e:
        return False, f"SMTP connection failed: {str(e)}"


@login_required
def sender_information(request):
    """Manage sender information and email addresses"""
    # Get or create sender information
    sender_info, created = SenderInformation.objects.get_or_create(
        user=request.user,
        defaults={
            'business_name': request.user.get_full_name() or request.user.username
        }
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_business':
            # Update business information
            sender_info.business_name = request.POST.get('business_name', '')
            sender_info.business_address = request.POST.get('business_address', '')
            sender_info.business_phone = request.POST.get('business_phone', '')
            sender_info.business_website = request.POST.get('business_website', '')
            sender_info.save()
            messages.success(request, 'Business information updated successfully.')
            return redirect('sender-information')
        
        elif action == 'add_email':
            # Add new email with SMTP configuration
            email = request.POST.get('email', '').strip()
            display_name = request.POST.get('display_name', '').strip()
            smtp_host = request.POST.get('smtp_host', '').strip()
            smtp_port = request.POST.get('smtp_port', '587')
            smtp_username = request.POST.get('smtp_username', '').strip()
            smtp_password = request.POST.get('smtp_password', '').strip()
            smtp_encryption = request.POST.get('smtp_encryption', 'tls')
            
            if email and smtp_host:
                # Check if email already exists
                if not SenderEmail.objects.filter(sender_info=sender_info, email=email).exists():
                    # If this is the first email, make it primary
                    is_primary = not sender_info.sender_emails.exists()
                    
                    # Default username to email if not provided
                    if not smtp_username:
                        smtp_username = email
                    
                    SenderEmail.objects.create(
                        sender_info=sender_info,
                        email=email,
                        display_name=display_name,
                        smtp_host=smtp_host,
                        smtp_port=int(smtp_port),
                        smtp_username=smtp_username,
                        smtp_password=smtp_password,
                        smtp_encryption=smtp_encryption,
                        is_primary=is_primary
                    )
                    messages.success(request, f'Email "{email}" added successfully. Use the test button to verify SMTP settings.')
                else:
                    messages.error(request, f'Email "{email}" already exists.')
            else:
                messages.error(request, 'Email and SMTP host are required.')
            return redirect('sender-information')
        
        elif action == 'update_email':
            # Update email SMTP configuration
            email_id = request.POST.get('email_id')
            try:
                email_obj = SenderEmail.objects.get(id=email_id, sender_info=sender_info)
                email_obj.display_name = request.POST.get('display_name', '').strip()
                email_obj.smtp_host = request.POST.get('smtp_host', '').strip()
                email_obj.smtp_port = int(request.POST.get('smtp_port', '587'))
                email_obj.smtp_username = request.POST.get('smtp_username', '').strip()
                
                # Only update password if provided
                new_password = request.POST.get('smtp_password', '').strip()
                if new_password:
                    email_obj.smtp_password = new_password
                
                email_obj.smtp_encryption = request.POST.get('smtp_encryption', 'tls')
                email_obj.is_verified = False  # Reset verification status
                email_obj.verification_error = ''
                email_obj.save()
                
                messages.success(request, 'Email settings updated successfully. Please test the connection.')
            except SenderEmail.DoesNotExist:
                messages.error(request, 'Email not found.')
            return redirect('sender-information')
        
        elif action == 'test_email':
            # Test SMTP connection
            email_id = request.POST.get('email_id')
            try:
                email_obj = SenderEmail.objects.get(id=email_id, sender_info=sender_info)
                
                # Test the connection
                success, message = test_smtp_connection(
                    email_obj.smtp_host,
                    email_obj.smtp_port,
                    email_obj.smtp_username,
                    email_obj.smtp_password,
                    email_obj.smtp_encryption,
                    email_obj.email
                )
                
                # Update verification status
                email_obj.is_verified = success
                email_obj.last_verified = timezone.now() if success else None
                email_obj.verification_error = '' if success else message
                email_obj.save()
                
                if success:
                    messages.success(request, message)
                else:
                    messages.error(request, message)
                    
            except SenderEmail.DoesNotExist:
                messages.error(request, 'Email not found.')
            return redirect('sender-information')
        
        elif action == 'delete_email':
            # Delete email
            email_id = request.POST.get('email_id')
            try:
                email_obj = SenderEmail.objects.get(id=email_id, sender_info=sender_info)
                was_primary = email_obj.is_primary
                email_obj.delete()
                
                # If deleted email was primary, make another one primary
                if was_primary and sender_info.sender_emails.exists():
                    new_primary = sender_info.sender_emails.first()
                    new_primary.is_primary = True
                    new_primary.save()
                
                messages.success(request, 'Email removed successfully.')
            except SenderEmail.DoesNotExist:
                messages.error(request, 'Email not found.')
            return redirect('sender-information')
        
        elif action == 'set_primary':
            # Set primary email
            email_id = request.POST.get('email_id')
            try:
                # Remove primary from all emails
                sender_info.sender_emails.update(is_primary=False)
                
                # Set new primary
                email_obj = SenderEmail.objects.get(id=email_id, sender_info=sender_info)
                email_obj.is_primary = True
                email_obj.save()
                
                messages.success(request, f'"{email_obj.email}" is now the primary email.')
            except SenderEmail.DoesNotExist:
                messages.error(request, 'Email not found.')
            return redirect('sender-information')
    
    # Get all sender emails
    sender_emails = sender_info.sender_emails.all()
    
    # Common SMTP presets
    smtp_presets = {
        'gmail': {'host': 'smtp.gmail.com', 'port': 587, 'encryption': 'tls'},
        'outlook': {'host': 'smtp-mail.outlook.com', 'port': 587, 'encryption': 'tls'},
        'yahoo': {'host': 'smtp.mail.yahoo.com', 'port': 587, 'encryption': 'tls'},
        'custom': {'host': '', 'port': 587, 'encryption': 'tls'},
    }
    
    context = {
        'sender_info': sender_info,
        'sender_emails': sender_emails,
        'smtp_presets': smtp_presets,
    }
    
    return render(request, 'accounts/sender_information.html', context)