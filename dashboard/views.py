from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from customer.models import Customer
from customer.forms import CustomerForm
from blog.models import Post
from blog.forms import PostForm
from email_campaign.models import EmailCampaign, TargetGroup
from datetime import datetime, timedelta


@login_required
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
    
    return render(request, 'dashboard/home.html', context)


@login_required
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
    
    return render(request, 'dashboard/customer_list.html', context)


@login_required
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
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'dashboard/blog_list.html', context)


@login_required
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


@login_required
def blog_detail(request, pk):
    """Display blog post details"""
    post = get_object_or_404(Post, pk=pk)
    
    # Check if user owns the post
    if post.author != request.user:
        messages.error(request, 'You can only view your own posts.')
        return redirect('dashboard:blog_list')
    
    return render(request, 'dashboard/blog_detail.html', {'post': post})


@login_required
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


@login_required
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
@login_required
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
    
    return render(request, 'dashboard/customer_form.html', {'form': form, 'action': 'Create'})


@login_required
def customer_detail(request, pk):
    """Display customer details"""
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'dashboard/customer_detail.html', {'customer': customer})


@login_required
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
    
    return render(request, 'dashboard/customer_form.html', {
        'form': form, 
        'action': 'Edit',
        'customer': customer
    })


@login_required
def customer_delete(request, pk):
    """Delete a customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Customer deleted successfully!')
        return redirect('dashboard:customer_list')
    
    return render(request, 'dashboard/customer_confirm_delete.html', {'customer': customer})


@login_required
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
