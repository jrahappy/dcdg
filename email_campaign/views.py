from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mass_mail
from django.conf import settings
from django.utils import timezone
from customer.models import Customer
from .models import TargetGroup, EmailCampaign, EmailLog
from .forms import EmailCampaignForm
from email_templates.models import EmailTemplate
import json


class TargetGroupCart:
    """Session-based shopping cart for building target groups"""
    
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('target_group_cart')
        if 'target_group_cart' not in request.session:
            cart = self.session['target_group_cart'] = {}
        self.cart = cart
    
    def add(self, customer_id):
        """Add a customer to the cart"""
        customer_id = str(customer_id)
        if customer_id not in self.cart:
            self.cart[customer_id] = True
            self.save()
    
    def remove(self, customer_id):
        """Remove a customer from the cart"""
        customer_id = str(customer_id)
        if customer_id in self.cart:
            del self.cart[customer_id]
            self.save()
    
    def get_customers(self):
        """Return Customer objects in the cart"""
        customer_ids = self.cart.keys()
        return Customer.objects.filter(id__in=customer_ids)
    
    def get_count(self):
        """Get number of customers in cart"""
        return len(self.cart)
    
    def clear(self):
        """Clear the cart"""
        self.session['target_group_cart'] = {}
        self.cart = {}
        self.save()
    
    def save(self):
        """Mark session as modified"""
        self.session.modified = True


@staff_member_required
def campaign_list(request):
    """List all email campaigns"""
    campaigns = EmailCampaign.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        campaigns = campaigns.filter(
            Q(name__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(target_group__name__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        campaigns = campaigns.filter(status=status_filter)
    
    # Calculate statistics
    sent_count = EmailCampaign.objects.filter(created_by=request.user, status='sent').count()
    draft_count = EmailCampaign.objects.filter(created_by=request.user, status='draft').count()
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(campaigns, 20)  # Show 20 campaigns per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'campaigns': campaigns,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'sent_count': sent_count,
        'draft_count': draft_count,
    }
    return render(request, 'email_campaign/campaign_list_daisyui.html', context)


@staff_member_required
def customer_selection(request):
    """Customer selection view with filters"""
    customers = Customer.objects.filter(is_active=True)
    cart = TargetGroupCart(request)
    
    # Apply filters
    search_query = request.GET.get('search', '')
    city_filter = request.GET.get('city', '')
    state_filter = request.GET.get('state', '')
    
    if search_query:
        customers = customers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company_name__icontains=search_query)
        )
    
    if city_filter:
        customers = customers.filter(city__icontains=city_filter)
    
    if state_filter:
        customers = customers.filter(state__icontains=state_filter)
    
    # Get unique cities and states for filter dropdowns
    cities = Customer.objects.values_list('city', flat=True).distinct().exclude(city='').order_by('city')
    states = Customer.objects.values_list('state', flat=True).distinct().exclude(state='').order_by('state')
    
    # Get IDs of customers already in cart
    cart_customer_ids = [int(id) for id in cart.cart.keys()]
    
    context = {
        'customers': customers,
        'cart_count': cart.get_count(),
        'cart_customer_ids': cart_customer_ids,
        'search_query': search_query,
        'city_filter': city_filter,
        'state_filter': state_filter,
        'cities': cities,
        'states': states,
    }
    return render(request, 'email_campaign/customer_selection.html', context)


@staff_member_required
@require_POST
def add_to_cart(request):
    """Add customers to target group cart"""
    cart = TargetGroupCart(request)
    customer_ids = request.POST.getlist('customer_ids[]')
    
    added_count = 0
    for customer_id in customer_ids:
        if Customer.objects.filter(id=customer_id).exists():
            cart.add(customer_id)
            added_count += 1
    
    return JsonResponse({
        'success': True,
        'added_count': added_count,
        'total_count': cart.get_count()
    })


@staff_member_required
@require_POST
def remove_from_cart(request):
    """Remove customer from target group cart"""
    cart = TargetGroupCart(request)
    customer_id = request.POST.get('customer_id')
    
    if customer_id:
        cart.remove(customer_id)
    
    return JsonResponse({
        'success': True,
        'total_count': cart.get_count()
    })


@staff_member_required
def target_group_cart_view(request):
    """View and manage target group cart"""
    cart = TargetGroupCart(request)
    customers = cart.get_customers()
    
    # Apply filters
    search_query = request.GET.get('search', '')
    city_filter = request.GET.get('city', '')
    state_filter = request.GET.get('state', '')
    
    if search_query:
        customers = customers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company_name__icontains=search_query)
        )
    
    if city_filter:
        customers = customers.filter(city__icontains=city_filter)
    
    if state_filter:
        customers = customers.filter(state__icontains=state_filter)
    
    # Get unique cities and states for filter dropdowns (from cart customers only)
    all_cart_customers = cart.get_customers()
    cities = all_cart_customers.values_list('city', flat=True).distinct().exclude(city='').order_by('city')
    states = all_cart_customers.values_list('state', flat=True).distinct().exclude(state='').order_by('state')
    
    if request.method == 'POST' and 'create_group' in request.POST:
        # Create target group from cart
        name = request.POST.get('group_name')
        description = request.POST.get('description', '')
        
        # Use all customers in cart, not filtered ones
        all_customers = cart.get_customers()
        
        if name and all_customers.exists():
            target_group = TargetGroup.objects.create(
                name=name,
                description=description,
                created_by=request.user
            )
            target_group.customers.set(all_customers)
            
            # Clear cart after creating group
            cart.clear()
            
            # Store target group in session for 3-step process
            request.session['campaign_creation'] = {
                'target_group_id': target_group.id,
                'step': 1
            }
            messages.success(request, f'Target group "{name}" created with {all_customers.count()} customers.')
            return redirect('email_campaign:campaign_create_step2')
        else:
            messages.error(request, 'Please provide a name and select at least one customer.')
    
    context = {
        'customers': customers,
        'cart_count': cart.get_count(),
        'search_query': search_query,
        'city_filter': city_filter,
        'state_filter': state_filter,
        'cities': cities,
        'states': states,
    }
    return render(request, 'email_campaign/target_group_cart.html', context)


@staff_member_required
def clear_cart(request):
    """Clear the target group cart"""
    cart = TargetGroupCart(request)
    cart.clear()
    messages.success(request, 'Target group cart cleared.')
    return redirect('email_campaign:customer_selection')


@staff_member_required
def campaign_create(request, target_group_id=None):
    """Create new email campaign"""
    if target_group_id:
        target_group = get_object_or_404(TargetGroup, id=target_group_id, created_by=request.user)
    else:
        # Redirect to select target group if none provided
        target_groups = TargetGroup.objects.filter(created_by=request.user)
        if not target_groups.exists():
            messages.error(request, 'Please create a target group first.')
            return redirect('email_campaign:customer_selection')
        
        if request.GET.get('target_group'):
            target_group = get_object_or_404(
                TargetGroup, 
                id=request.GET.get('target_group'), 
                created_by=request.user
            )
        else:
            return render(request, 'email_campaign/select_target_group.html', {
                'target_groups': target_groups
            })
    
    if request.method == 'POST':
        form = EmailCampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.target_group = target_group
            campaign.created_by = request.user
            campaign.total_recipients = target_group.customer_count
            campaign.save()
            
            messages.success(request, f'Campaign "{campaign.name}" created successfully.')
            return redirect('email_campaign:campaign_detail', pk=campaign.id)
    else:
        form = EmailCampaignForm()
    
    context = {
        'form': form,
        'target_group': target_group,
        'action': 'Create'
    }
    return render(request, 'email_campaign/campaign_form.html', context)


@staff_member_required
def campaign_detail(request, pk):
    """View campaign details"""
    campaign = get_object_or_404(EmailCampaign, pk=pk, created_by=request.user)
    
    context = {
        'campaign': campaign,
        'customers': campaign.target_group.customers.all()[:10],  # Show first 10
    }
    return render(request, 'email_campaign/campaign_detail.html', context)


@staff_member_required
@require_POST
def send_campaign(request, pk):
    """Send email campaign"""
    campaign = get_object_or_404(EmailCampaign, pk=pk, created_by=request.user)
    
    if campaign.status != 'draft':
        messages.error(request, 'This campaign has already been sent or is in progress.')
        return redirect('email_campaign:campaign_detail', pk=pk)
    
    # Update campaign status
    campaign.status = 'sending'
    campaign.save()
    
    # Prepare emails
    email_template = campaign.email_template
    from_email = email_template.sender_email if email_template else (campaign.from_email or settings.DEFAULT_FROM_EMAIL)
    subject = email_template.subject if email_template else campaign.subject
    customers = campaign.target_group.customers.all()
    
    messages_to_send = []
    for customer in customers:
        # Create email log entry
        EmailLog.objects.create(
            campaign=campaign,
            customer=customer,
            status='pending'
        )
        
        # Prepare email content with template variables
        if email_template:
            # Use email template with variable substitution
            content = email_template.html_content or email_template.plain_content
            # Basic variable substitution (in a real system, you'd use a proper template engine)
            content = content.replace('{{first_name}}', customer.first_name or '')
            content = content.replace('{{last_name}}', customer.last_name or '')
            content = content.replace('{{email}}', customer.email or '')
            content = content.replace('{{company_name}}', customer.company_name or '')
            # Add more variable substitutions as needed
        else:
            # Use legacy content field
            content = campaign.content
        
        # Prepare email
        message = (
            subject,
            content,
            from_email,
            [customer.email]
        )
        messages_to_send.append(message)
    
    # Send emails (in production, this should be done asynchronously)
    try:
        sent_count = send_mass_mail(messages_to_send, fail_silently=False)
        
        # Update logs and campaign
        EmailLog.objects.filter(campaign=campaign).update(
            status='sent',
            sent_at=timezone.now()
        )
        
        campaign.sent_count = sent_count
        campaign.mark_as_sent()
        
        messages.success(request, f'Campaign sent successfully to {sent_count} recipients.')
    except Exception as e:
        # Update campaign status
        campaign.status = 'failed'
        campaign.save()
        
        # Update logs
        EmailLog.objects.filter(campaign=campaign).update(
            status='failed',
            error_message=str(e)
        )
        
        messages.error(request, f'Failed to send campaign: {str(e)}')
    
    return redirect('email_campaign:campaign_detail', pk=pk)


@staff_member_required
def campaign_delete(request, pk):
    """Delete campaign"""
    campaign = get_object_or_404(EmailCampaign, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        name = campaign.name
        campaign.delete()
        messages.success(request, f'Campaign "{name}" deleted successfully.')
        return redirect('email_campaign:campaign_list')
    
    return render(request, 'email_campaign/campaign_confirm_delete.html', {'campaign': campaign})


@staff_member_required
def target_group_list(request):
    """List all target groups"""
    target_groups = TargetGroup.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        target_groups = target_groups.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(target_groups, 20)  # Show 20 target groups per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'target_groups': target_groups,
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'email_campaign/target_group_list_daisyui.html', context)


@staff_member_required
def target_group_detail(request, pk):
    """View target group details"""
    target_group = get_object_or_404(TargetGroup, pk=pk, created_by=request.user)
    customers = target_group.customers.all()
    campaigns = EmailCampaign.objects.filter(target_group=target_group)
    
    context = {
        'target_group': target_group,
        'customers': customers,
        'campaigns': campaigns,
    }
    return render(request, 'email_campaign/target_group_detail.html', context)


@staff_member_required
def target_group_edit(request, pk):
    """Edit target group"""
    target_group = get_object_or_404(TargetGroup, pk=pk, created_by=request.user)
    
    # Get all active customers
    all_customers = Customer.objects.filter(is_active=True).order_by('company_name', 'last_name', 'first_name')
    
    # Get current customers in the group
    current_customer_ids = list(target_group.customers.values_list('id', flat=True))
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        selected_customers = request.POST.getlist('customers')
        
        if name:
            target_group.name = name
            target_group.description = description
            target_group.save()
            
            # Update customers
            if selected_customers:
                target_group.customers.set(selected_customers)
            else:
                target_group.customers.clear()
            
            messages.success(request, f'Target group "{name}" updated successfully.')
            return redirect('email_campaign:target_group_detail', pk=pk)
        else:
            messages.error(request, 'Please provide a name for the target group.')
    
    context = {
        'target_group': target_group,
        'all_customers': all_customers,
        'current_customer_ids': current_customer_ids,
    }
    return render(request, 'email_campaign/target_group_edit.html', context)


@staff_member_required
def target_group_delete(request, pk):
    """Delete target group"""
    target_group = get_object_or_404(TargetGroup, pk=pk, created_by=request.user)
    
    # Check if any campaigns are using this target group
    campaign_count = EmailCampaign.objects.filter(target_group=target_group).count()
    
    if request.method == 'POST':
        if campaign_count > 0:
            messages.error(request, f'Cannot delete this target group. It is used by {campaign_count} campaign(s).')
        else:
            name = target_group.name
            target_group.delete()
            messages.success(request, f'Target group "{name}" deleted successfully.')
            return redirect('email_campaign:target_group_list')
    
    context = {
        'target_group': target_group,
        'campaign_count': campaign_count,
    }
    return render(request, 'email_campaign/target_group_confirm_delete.html', context)


# 3-Step Marketing Campaign Creation Views

@staff_member_required
def campaign_create_step1(request):
    """Step 1: Select Target Group"""
    target_groups = TargetGroup.objects.filter(created_by=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        target_group_id = request.POST.get('target_group_id')
        if target_group_id:
            # Store in session and proceed to step 2
            request.session['campaign_creation'] = {
                'target_group_id': target_group_id,
                'step': 1
            }
            return redirect('email_campaign:campaign_create_step2')
        else:
            messages.error(request, 'Please select a target group.')
    
    context = {
        'target_groups': target_groups,
        'step': 1,
        'step_title': 'Select Target Group'
    }
    return render(request, 'email_campaign/campaign_create_step1.html', context)


@staff_member_required
def campaign_create_step2(request):
    """Step 2: Select Email Template"""
    # Check if step 1 is completed
    campaign_data = request.session.get('campaign_creation')
    if not campaign_data or campaign_data.get('step', 0) < 1:
        messages.error(request, 'Please complete step 1 first.')
        return redirect('email_campaign:campaign_create_step1')
    
    # Get target group for context
    target_group = get_object_or_404(TargetGroup, id=campaign_data['target_group_id'], created_by=request.user)
    
    # Get available email templates
    email_templates = EmailTemplate.objects.filter(status='active').order_by('-updated_at')
    
    if request.method == 'POST':
        email_template_id = request.POST.get('email_template_id')
        if email_template_id:
            # Update session and proceed to step 3
            campaign_data['email_template_id'] = email_template_id
            campaign_data['step'] = 2
            request.session['campaign_creation'] = campaign_data
            return redirect('email_campaign:campaign_create_step3')
        else:
            messages.error(request, 'Please select an email template.')
    
    context = {
        'target_group': target_group,
        'email_templates': email_templates,
        'step': 2,
        'step_title': 'Select Email Template'
    }
    return render(request, 'email_campaign/campaign_create_step2.html', context)


@staff_member_required
def campaign_create_step3(request):
    """Step 3: Preview and Create Campaign"""
    # Check if previous steps are completed
    campaign_data = request.session.get('campaign_creation')
    if not campaign_data or campaign_data.get('step', 0) < 2:
        messages.error(request, 'Please complete the previous steps first.')
        return redirect('email_campaign:campaign_create_step1')
    
    # Get objects for preview
    target_group = get_object_or_404(TargetGroup, id=campaign_data['target_group_id'], created_by=request.user)
    email_template = get_object_or_404(EmailTemplate, id=campaign_data['email_template_id'])
    
    if request.method == 'POST':
        action = request.POST.get('action')
        campaign_name = request.POST.get('campaign_name', f'{email_template.title} - {target_group.name}')
        
        if action == 'create_draft':
            # Create campaign as draft
            campaign = EmailCampaign.objects.create(
                name=campaign_name,
                subject=email_template.subject,
                email_template=email_template,
                target_group=target_group,
                created_by=request.user,
                total_recipients=target_group.customer_count,
                status='draft'
            )
            
            # Clear session data
            if 'campaign_creation' in request.session:
                del request.session['campaign_creation']
            
            messages.success(request, f'Campaign "{campaign_name}" created as draft.')
            return redirect('email_campaign:campaign_detail', pk=campaign.id)
            
        elif action == 'create_and_send':
            # Create campaign and send immediately
            campaign = EmailCampaign.objects.create(
                name=campaign_name,
                subject=email_template.subject,
                email_template=email_template,
                target_group=target_group,
                created_by=request.user,
                total_recipients=target_group.customer_count,
                status='draft'
            )
            
            # Clear session data
            if 'campaign_creation' in request.session:
                del request.session['campaign_creation']
            
            # Send the campaign immediately
            return redirect('email_campaign:send_campaign', pk=campaign.id)
    
    # Get first few customers for preview
    sample_customers = target_group.customers.all()[:3]
    
    context = {
        'target_group': target_group,
        'email_template': email_template,
        'sample_customers': sample_customers,
        'step': 3,
        'step_title': 'Preview & Create'
    }
    return render(request, 'email_campaign/campaign_create_step3.html', context)
