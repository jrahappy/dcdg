from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from customer.models import Customer
from customer.forms import CustomerForm
from blog.models import Post
from blog.forms import PostForm
from email_campaign.models import EmailCampaign, TargetGroup
from customer_portal.models import Notification
from datetime import datetime, timedelta

User = get_user_model()


@staff_member_required
def dashboard_home(request):
    # Get statistics for dashboard
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(is_active=True).count()
    
    # Customers added in last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    new_customers = Customer.objects.filter(date_joined__gte=thirty_days_ago).count()
    
    # Recent customers for display
    recent_customers = Customer.objects.order_by('-date_joined')[:5]
    
    # Get recent campaigns
    recent_campaigns = EmailCampaign.objects.filter(
        created_by=request.user
    ).select_related('target_group').order_by('-created_at')[:5]
    
    # Get campaign statistics
    total_campaigns = EmailCampaign.objects.filter(created_by=request.user).count()
    sent_campaigns = EmailCampaign.objects.filter(created_by=request.user, status='sent').count()
    draft_campaigns = EmailCampaign.objects.filter(created_by=request.user, status='draft').count()
    
    # Get recent blog posts
    recent_posts = Post.objects.filter(
        author=request.user
    ).order_by('-created_at')[:5]
    
    # Get blog statistics
    total_posts = Post.objects.filter(author=request.user).count()
    published_posts = Post.objects.filter(author=request.user, status='published').count()
    draft_posts = Post.objects.filter(author=request.user, status='draft').count()
    
    context = {
        'total_customers': total_customers,
        'active_customers': active_customers,
        'new_customers': new_customers,
        'recent_customers': recent_customers,
        'recent_campaigns': recent_campaigns,
        'total_campaigns': total_campaigns,
        'sent_campaigns': sent_campaigns,
        'draft_campaigns': draft_campaigns,
        'recent_posts': recent_posts,
        'total_posts': total_posts,
        'published_posts': published_posts,
        'draft_posts': draft_posts,
    }
    
    # Use DaisyUI template if specified in GET parameter or settings
    use_daisyui = request.GET.get('ui') == 'daisyui' or request.session.get('use_daisyui', True)
    template = 'dashboard/home_daisyui.html' if use_daisyui else 'dashboard/home.html'
    
    return render(request, template, context)


@staff_member_required
def customer_list(request):
    customers = Customer.objects.all().order_by('-date_joined')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        customers = customers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company_name__icontains=search_query)
        )
    
    # Get rows per page from request, default to 20
    rows_per_page = request.GET.get('rows', '20')
    try:
        rows_per_page = int(rows_per_page)
        if rows_per_page not in [10, 20, 50, 100]:
            rows_per_page = 20
    except ValueError:
        rows_per_page = 20
    
    # Pagination
    paginator = Paginator(customers, rows_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'customers': page_obj,
        'search_query': search_query,
        'page_obj': page_obj,
        'rows_per_page': rows_per_page,
    }
    
    return render(request, 'dashboard/customer_list_daisyui.html', context)


@staff_member_required
def blog_list(request):
    # Get posts for the current user
    posts = Post.objects.filter(author=request.user).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter in ['draft', 'published']:
        posts = posts.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(posts, 20)  # Show 20 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'posts': posts,
        'page_obj': page_obj,
        'object_list': page_obj,  # For the generic template
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    # Use DaisyUI template
    template = 'dashboard/blog_list_daisyui.html'
    return render(request, template, context)


@staff_member_required
def blog_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, 'Post created successfully!')
            return redirect('dashboard:blog_list')
    else:
        form = PostForm()
    
    return render(request, 'dashboard/blog_form.html', {'form': form, 'action': 'Create'})


@staff_member_required
def blog_detail(request, pk):
    """Display blog post details"""
    post = get_object_or_404(Post, pk=pk)
    
    # Check if user owns the post
    if post.author != request.user:
        messages.error(request, 'You can only view your own posts.')
        return redirect('dashboard:blog_list')
    
    return render(request, 'dashboard/blog_detail.html', {'post': post})


@staff_member_required
def blog_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # Check if user owns the post
    if post.author != request.user:
        messages.error(request, 'You can only edit your own posts.')
        return redirect('dashboard:blog_list')
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('dashboard:blog_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)
    
    return render(request, 'dashboard/blog_form.html', {'form': form, 'action': 'Edit', 'post': post})


@staff_member_required
def blog_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # Check if user owns the post
    if post.author != request.user:
        messages.error(request, 'You can only delete your own posts.')
        return redirect('dashboard:blog_list')
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted successfully!')
        return redirect('dashboard:blog_list')
    
    return render(request, 'dashboard/blog_confirm_delete.html', {'post': post})


# Customer CRUD Views
@staff_member_required
def customer_create(request):
    """Create a new customer"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.user = request.user  # Associate with current user
            customer.save()
            messages.success(request, 'Customer created successfully!')
            return redirect('dashboard:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    return render(request, 'dashboard/customer_form_daisyui.html', {'form': form, 'action': 'Create'})


@staff_member_required
def customer_detail(request, pk):
    """Display customer details"""
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'dashboard/customer_detail_daisyui.html', {'customer': customer})


@staff_member_required
def customer_edit(request, pk):
    """Edit an existing customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated successfully!')
            return redirect('dashboard:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'dashboard/customer_form_daisyui.html', {
        'form': form, 
        'action': 'Edit',
        'customer': customer
    })


@staff_member_required
def customer_delete(request, pk):
    """Delete a customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Customer deleted successfully!')
        return redirect('dashboard:customer_list')
    
    return render(request, 'dashboard/customer_confirm_delete_daisyui.html', {'customer': customer})


@staff_member_required
def global_search(request):
    """Global search across customers, campaigns, and target groups"""
    query = request.GET.get('q', '').strip()
    
    results = {
        'customers': [],
        'campaigns': [],
        'target_groups': [],
        'query': query
    }
    
    if query:
        # Search customers
        customers = Customer.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(company_name__icontains=query)
        ).order_by('first_name', 'last_name')[:10]  # Limit to 10 results
        results['customers'] = customers
        
        # Search email campaigns
        campaigns = EmailCampaign.objects.filter(
            Q(name__icontains=query) |
            Q(subject__icontains=query) |
            Q(target_group__name__icontains=query),
            created_by=request.user
        ).select_related('target_group').order_by('-created_at')[:10]
        results['campaigns'] = campaigns
        
        # Search target groups
        target_groups = TargetGroup.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query),
            created_by=request.user
        ).order_by('-created_at')[:10]
        results['target_groups'] = target_groups
    
    return render(request, 'dashboard/global_search.html', results)


@staff_member_required
def notification_manage(request):
    """Manage notifications for customers"""
    
    # Get all notifications
    notifications = Notification.objects.all().select_related('user').order_by('-created_at')
    
    # Filter by user
    user_filter = request.GET.get('user')
    if user_filter:
        notifications = notifications.filter(user_id=user_filter)
    
    # Filter by type
    type_filter = request.GET.get('type')
    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)
    
    # Filter by priority
    priority_filter = request.GET.get('priority')
    if priority_filter:
        notifications = notifications.filter(priority=priority_filter)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query) |
            Q(message__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get users for filter dropdown
    users_with_notifications = User.objects.filter(
        notifications__isnull=False
    ).distinct().order_by('username')
    
    # Get statistics
    from datetime import date
    stats = {
        'total': Notification.objects.count(),
        'unread': Notification.objects.filter(is_read=False).count(),
        'high_priority': Notification.objects.filter(priority='high').count() + Notification.objects.filter(priority='urgent').count(),
        'today': Notification.objects.filter(created_at__date=date.today()).count(),
    }
    
    context = {
        'notifications': page_obj,
        'page_obj': page_obj,
        'users': users_with_notifications,
        'notification_types': Notification.NOTIFICATION_TYPES,
        'priority_levels': Notification.PRIORITY_LEVELS,
        'user_filter': user_filter,
        'type_filter': type_filter,
        'priority_filter': priority_filter,
        'search_query': search_query,
        'stats': stats,
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'dashboard/notification_manage_daisyui.html', context)


@staff_member_required
def notification_create(request):
    """Create a new notification"""
    
    if request.method == 'POST':
        # Get form data
        user_ids = request.POST.getlist('users')
        title = request.POST.get('title')
        message = request.POST.get('message')
        notification_type = request.POST.get('notification_type')
        priority = request.POST.get('priority')
        link = request.POST.get('link')
        
        # Create notifications for selected users
        if user_ids and title and message:
            created_count = 0
            for user_id in user_ids:
                try:
                    user = User.objects.get(pk=user_id)
                    Notification.objects.create(
                        user=user,
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        priority=priority,
                        link=link if link else ''
                    )
                    created_count += 1
                except User.DoesNotExist:
                    continue
            
            messages.success(request, f'Created {created_count} notifications successfully!')
            return redirect('dashboard:notification_manage')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    # Get all users for selection
    users = User.objects.filter(is_active=True).order_by('username')
    
    context = {
        'users': users,
        'notification_types': Notification.NOTIFICATION_TYPES,
        'priority_levels': Notification.PRIORITY_LEVELS,
    }
    
    return render(request, 'dashboard/notification_create_daisyui.html', context)


@staff_member_required
def notification_delete(request, pk):
    """Delete a notification"""
    
    notification = get_object_or_404(Notification, pk=pk)
    
    if request.method == 'POST':
        notification.delete()
        messages.success(request, 'Notification deleted successfully!')
        return redirect('dashboard:notification_manage')
    
    return render(request, 'dashboard/notification_confirm_delete.html', {
        'notification': notification
    })


@staff_member_required
def notification_list(request):
    """Return notification list for HTMX requests"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Mark this as an HTMX partial response
    if request.headers.get('HX-Request'):
        return render(request, 'dashboard/partials/notification_list.html', {
            'notifications': notifications
        })
    
    # Regular request fallback
    return JsonResponse({
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat() if n.created_at else None
            }
            for n in notifications
        ]
    })


@staff_member_required
def notification_bulk_action(request):
    """Handle bulk actions on notifications"""
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notification_ids = request.POST.getlist('notification_ids')
        
        if not notification_ids:
            return JsonResponse({'error': 'No notifications selected'}, status=400)
        
        notifications = Notification.objects.filter(pk__in=notification_ids)
        
        if action == 'delete':
            count = notifications.count()
            notifications.delete()
            messages.success(request, f'Deleted {count} notifications.')
        elif action == 'mark_read':
            count = notifications.filter(is_read=False).update(is_read=True)
            messages.success(request, f'Marked {count} notifications as read.')
        elif action == 'mark_unread':
            count = notifications.filter(is_read=True).update(is_read=False, read_at=None)
            messages.success(request, f'Marked {count} notifications as unread.')
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)
