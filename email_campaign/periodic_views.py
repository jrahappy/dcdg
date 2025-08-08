from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta, time

from .models import PeriodicCampaign, PeriodicCampaignLog, EmailCampaign, EmailLog
from .forms import PeriodicCampaignForm, PeriodicCampaignEditForm
from email_templates.models import EmailTemplate


@staff_member_required
def periodic_campaign_list(request):
    """List all periodic campaigns"""
    campaigns = PeriodicCampaign.objects.select_related(
        'target_group', 'email_template', 'created_by'
    ).annotate(
        log_count=Count('logs')
    )
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        campaigns = campaigns.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(target_group__name__icontains=search_query)
        )
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        campaigns = campaigns.filter(status=status_filter)
    
    # Frequency filter
    frequency_filter = request.GET.get('frequency', '')
    if frequency_filter:
        campaigns = campaigns.filter(frequency=frequency_filter)
    
    # Pagination
    paginator = Paginator(campaigns, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'frequency_filter': frequency_filter,
        'status_choices': PeriodicCampaign.STATUS_CHOICES,
        'frequency_choices': PeriodicCampaign.FREQUENCY_CHOICES,
    }
    
    return render(request, 'email_campaign/periodic_campaign_list_daisyui.html', context)


@staff_member_required
def periodic_campaign_create(request):
    """Create a new periodic campaign"""
    if request.method == 'POST':
        form = PeriodicCampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            
            # Calculate next run based on start date and frequency
            start_date = form.cleaned_data['start_date']
            campaign.next_run = datetime.combine(start_date, time.min)
            
            campaign.save()
            messages.success(request, 'Periodic campaign created successfully!')
            return redirect('email_campaign:periodic_campaign_detail', pk=campaign.pk)
        else:
            # Add error message if form is invalid
            messages.error(request, 'Please correct the errors below.')
            print("Form errors:", form.errors)  # Debug print
    else:
        form = PeriodicCampaignForm()
    
    context = {
        'form': form,
        'is_create': True,
    }
    
    return render(request, 'email_campaign/periodic_campaign_form_daisyui.html', context)


@staff_member_required
def periodic_campaign_edit(request, pk):
    """Edit an existing periodic campaign"""
    campaign = get_object_or_404(PeriodicCampaign, pk=pk)
    
    if request.method == 'POST':
        form = PeriodicCampaignEditForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, 'Periodic campaign updated successfully!')
            return redirect('email_campaign:periodic_campaign_detail', pk=campaign.pk)
    else:
        form = PeriodicCampaignEditForm(instance=campaign)
    
    context = {
        'form': form,
        'campaign': campaign,
        'is_create': False,
    }
    
    return render(request, 'email_campaign/periodic_campaign_form_daisyui.html', context)


@staff_member_required
def periodic_campaign_detail(request, pk):
    """View periodic campaign details with logs"""
    campaign = get_object_or_404(
        PeriodicCampaign.objects.select_related('target_group', 'email_template', 'created_by'),
        pk=pk
    )
    
    # Get recent logs
    logs = campaign.logs.select_related('email_campaign').order_by('-started_at')[:10]
    
    # Calculate statistics
    total_logs = campaign.logs.count()
    successful_logs = campaign.logs.filter(status='completed').count()
    failed_logs = campaign.logs.filter(status='failed').count()
    
    context = {
        'campaign': campaign,
        'logs': logs,
        'total_logs': total_logs,
        'successful_logs': successful_logs,
        'failed_logs': failed_logs,
        'success_rate': (successful_logs / total_logs * 100) if total_logs > 0 else 0,
    }
    
    return render(request, 'email_campaign/periodic_campaign_detail.html', context)


@staff_member_required
def periodic_campaign_delete(request, pk):
    """Delete a periodic campaign"""
    campaign = get_object_or_404(PeriodicCampaign, pk=pk)
    
    if request.method == 'POST':
        campaign.delete()
        messages.success(request, 'Periodic campaign deleted successfully!')
        return redirect('email_campaign:periodic_campaign_list')
    
    return redirect('email_campaign:periodic_campaign_detail', pk=pk)


@staff_member_required
def periodic_campaign_logs(request, pk):
    """View all logs for a periodic campaign"""
    campaign = get_object_or_404(PeriodicCampaign, pk=pk)
    logs = campaign.logs.select_related('email_campaign').order_by('-started_at')
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'campaign': campaign,
        'page_obj': page_obj,
    }
    
    return render(request, 'email_campaign/periodic_campaign_logs.html', context)


@staff_member_required
def periodic_campaign_toggle_status(request, pk):
    """Toggle periodic campaign status between active and paused"""
    campaign = get_object_or_404(PeriodicCampaign, pk=pk)
    
    if request.method == 'POST':
        if campaign.status == 'active':
            campaign.status = 'paused'
            messages.info(request, 'Periodic campaign paused.')
        elif campaign.status == 'paused':
            campaign.status = 'active'
            messages.success(request, 'Periodic campaign activated.')
        else:
            messages.error(request, 'Cannot toggle status of completed campaign.')
            return redirect('email_campaign:periodic_campaign_detail', pk=pk)
        
        campaign.save()
    
    return redirect('email_campaign:periodic_campaign_detail', pk=pk)


@staff_member_required
@require_POST
def periodic_campaign_test_run(request, pk):
    """Execute a test run of the periodic campaign"""
    campaign = get_object_or_404(PeriodicCampaign, pk=pk)
    
    # Create a log entry for this test run
    log = PeriodicCampaignLog.objects.create(
        periodic_campaign=campaign,
        status='running',
        recipients_count=0,
        sent_count=0,
        failed_count=0
    )
    
    try:
        # Get the email template
        template = campaign.email_template
        if not template:
            raise ValueError("No email template associated with this campaign")
        
        # Get target group customers
        customers = campaign.target_group.customers.filter(email__isnull=False)
        log.recipients_count = customers.count()
        log.save()
        
        if log.recipients_count == 0:
            raise ValueError("No customers with email addresses in the target group")
        
        # Create an email campaign for this run
        email_campaign = EmailCampaign.objects.create(
            name=f"{campaign.name} - Test Run {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            subject=template.subject,
            content=template.html_content if template.has_html_content() else template.plain_content,
            from_email=template.sender_email.email if template.sender_email else '',
            target_group=campaign.target_group,
            campaign_type='periodic',
            status='sending',
            created_by=request.user,
            total_recipients=log.recipients_count
        )
        
        log.email_campaign = email_campaign
        log.save()
        
        # Process each customer (in a real implementation, this would be done asynchronously)
        sent_count = 0
        failed_count = 0
        
        for customer in customers[:5]:  # Limit to 5 for test run
            try:
                # Replace template variables
                content = email_campaign.content
                subject = email_campaign.subject
                
                # Replace variables
                replacements = {
                    '{{first_name}}': customer.first_name or '',
                    '{{last_name}}': customer.last_name or '',
                    '{{email}}': customer.email,
                    '{{company_name}}': customer.company_name or '',
                    '{{target_link}}': campaign.get_full_target_link(),
                    '{{unsubscribe_link}}': f"http://example.com/unsubscribe/{customer.id}",
                    '{{current_year}}': str(timezone.now().year),
                    '{{current_date}}': timezone.now().strftime('%B %d, %Y'),
                }
                
                for var, value in replacements.items():
                    content = content.replace(var, value)
                    subject = subject.replace(var, value)
                
                # Create email log entry
                EmailLog.objects.create(
                    campaign=email_campaign,
                    customer=customer,
                    status='sent',
                    sent_at=timezone.now()
                )
                
                sent_count += 1
                
                # In a real implementation, you would actually send the email here
                # For now, we just simulate it
                
            except Exception as e:
                # Log failed email
                EmailLog.objects.create(
                    campaign=email_campaign,
                    customer=customer,
                    status='failed',
                    error_message=str(e)
                )
                failed_count += 1
        
        # Update counts
        log.sent_count = sent_count
        log.failed_count = failed_count
        log.status = 'completed'
        log.completed_at = timezone.now()
        log.save()
        
        # Update email campaign
        email_campaign.status = 'sent'
        email_campaign.sent_time = timezone.now()
        email_campaign.sent_count = sent_count
        email_campaign.failed_count = failed_count
        email_campaign.save()
        
        # Update periodic campaign stats
        campaign.last_run = timezone.now()
        campaign.total_sent += sent_count
        campaign.save()
        
        messages.success(
            request, 
            f'Test run completed! Sent to {sent_count} customers (limited to 5 for testing). '
            f'{failed_count} failed.'
        )
        
    except Exception as e:
        log.status = 'failed'
        log.error_message = str(e)
        log.completed_at = timezone.now()
        log.save()
        
        messages.error(request, f'Test run failed: {str(e)}')
    
    return redirect('email_campaign:periodic_campaign_detail', pk=pk)