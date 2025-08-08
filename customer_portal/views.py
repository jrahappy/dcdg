from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone

from customer.models import Customer, CustomerAddress
from sales.models import Invoice
from .forms import ProfileForm, AddressForm
from .models import Notification


@login_required
def dashboard(request):
    """Customer dashboard overview"""
    # Get or create customer profile
    customer, created = Customer.objects.get_or_create(
        user=request.user,
        defaults={
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
        },
    )

    # Get recent orders
    recent_orders = Invoice.objects.filter(
        user=request.user, is_shop_order=True
    ).order_by("-created_at")[:5]

    # Get saved addresses
    saved_addresses = CustomerAddress.objects.filter(
        Q(user=request.user) | Q(customer=customer)
    ).filter(is_active=True)[:3]

    context = {
        "customer": customer,
        "recent_orders": recent_orders,
        "saved_addresses": saved_addresses,
        "total_orders": Invoice.objects.filter(
            user=request.user, is_shop_order=True
        ).count(),
    }

    return render(request, "customer_portal/dashboard.html", context)


@login_required
def order_list(request):
    """List all orders for the logged-in customer"""
    customer = Customer.objects.filter(user=request.user).first()
    # Get all orders for the user
    # order_queryset = Invoice.objects.filter(user=request.user).order_by("-created_at")
    order_queryset = (
        Invoice.objects.filter(Q(customer=customer) | Q(user=request.user)).order_by(
            "-created_at"
        )
        # if customer
        # else Invoice.objects.filter(user=request.user, is_shop_order=True).order_by(
        #     "-created_at"
        # )
    )

    # Pagination
    paginator = Paginator(order_queryset, 10)
    page_number = request.GET.get("page")
    orders = paginator.get_page(page_number)

    context = {
        "orders": orders,
        "object_list": orders,  # For template compatibility
        "page_obj": orders,
        "is_paginated": orders.has_other_pages(),
        "paginator": paginator,
    }

    return render(request, "customer_portal/order_list.html", context)


@login_required
def order_detail(request, pk):
    """Order detail view for customers"""
    # Only allow viewing own orders
    order = get_object_or_404(Invoice, pk=pk)
    # order = get_object_or_404(Invoice, pk=pk, user=request.user, is_shop_order=True)

    return render(request, "customer_portal/order_detail.html", {"order": order})


@login_required
def profile_view(request):
    """View and edit customer profile"""
    customer, created = Customer.objects.get_or_create(
        user=request.user,
        defaults={
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
        },
    )

    # Get the default address
    default_address = CustomerAddress.objects.filter(
        customer=customer, 
        is_default=True, 
        is_active=True
    ).first()

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            # Update user model as well
            request.user.first_name = customer.first_name
            request.user.last_name = customer.last_name
            request.user.email = customer.email
            request.user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("customer_portal:profile")
    else:
        form = ProfileForm(instance=customer)

    # Get recent notifications
    recent_notifications = Notification.objects.filter(
        user=request.user
    )[:5]
    
    unread_notification_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return render(
        request, "customer_portal/profile.html", {
            "form": form, 
            "customer": customer,
            "default_address": default_address,
            "recent_notifications": recent_notifications,
            "unread_notification_count": unread_notification_count
        }
    )


@login_required
def address_list(request):
    """List all saved addresses"""
    # Get addresses linked to user or their customer profile
    # cust = request.user.customer_set.first()
    # customer = Customer.objects.filter(user=request.user).first()
    # If customer profile exists, filter addresses accordingly
    # If not, just filter by user
    # customer = Customer.objects.filter(Q(user=request.user)).first()
    # Get or create customer for the user
    try:
        customer = request.user.customer
    except Customer.DoesNotExist:
        customer = Customer.objects.create(
            user=request.user,
            email=request.user.email,
            first_name=request.user.first_name or '',
            last_name=request.user.last_name or '',
            company_category='customer',
            is_active=True
        )

    # Get all addresses for this user (either directly linked to user or through customer)
    addresses = CustomerAddress.objects.filter(
        Q(user=request.user) | Q(customer=customer)
    ).filter(is_active=True).distinct()

    return render(
        request, "customer_portal/address_list.html", {
            "addresses": addresses,
            "object_list": addresses  # For template compatibility
        }
    )


@login_required
def address_create(request):
    """Create a new address"""
    user = request.user
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = user

            # Also link to customer if exists
            try:
                customer = user.customer
                address.customer = customer
            except Customer.DoesNotExist:
                # Create customer if it doesn't exist
                customer = Customer.objects.create(
                    user=user,
                    email=user.email,
                    first_name=user.first_name or '',
                    last_name=user.last_name or '',
                    company_category='customer',
                    is_active=True
                )
                address.customer = customer
            address.save()
            messages.success(request, "Address added successfully!")
            return redirect("customer_portal:address_list")
    else:
        form = AddressForm()

    return render(request, "customer_portal/address_form.html", {"form": form})


@login_required
def address_update(request, pk):
    """Update an existing address"""
    # Only allow editing own addresses
    customer = Customer.objects.filter(user=request.user).first()
    if customer:
        address = get_object_or_404(
            CustomerAddress,
            Q(user=request.user) | Q(customer=customer),
            pk=pk,
            is_active=True,
        )
    else:
        address = get_object_or_404(
            CustomerAddress, user=request.user, pk=pk, is_active=True
        )

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated successfully!")
            return redirect("customer_portal:address_list")
    else:
        form = AddressForm(instance=address)

    return render(
        request,
        "customer_portal/address_form.html",
        {"form": form, "object": address},  # For template compatibility
    )


@login_required
def address_delete(request, pk):
    """Delete an address (soft delete)"""
    # Only allow deleting own addresses
    customer = Customer.objects.filter(user=request.user).first()
    if customer:
        address = get_object_or_404(
            CustomerAddress,
            Q(user=request.user) | Q(customer=customer),
            pk=pk,
            is_active=True,
        )
    else:
        address = get_object_or_404(
            CustomerAddress, user=request.user, pk=pk, is_active=True
        )

    if request.method == "POST":
        # Soft delete
        address.is_active = False
        address.save()
        messages.success(request, "Address deleted successfully!")
        return redirect("customer_portal:address_list")

    return render(
        request,
        "customer_portal/address_confirm_delete.html",
        {"address": address, "object": address},  # For template compatibility
    )


@login_required
def set_default_address(request, pk):
    """Set an address as default via AJAX"""
    if request.method == "POST":
        customer = Customer.objects.filter(user=request.user).first()
        if customer:
            address = get_object_or_404(
                CustomerAddress,
                Q(user=request.user) | Q(customer=customer),
                pk=pk,
                is_active=True,
            )
        else:
            address = get_object_or_404(
                CustomerAddress, user=request.user, pk=pk, is_active=True
            )

        address.is_default = True
        address.save()  # This will handle unsetting other defaults

        return JsonResponse({"success": True})

    return JsonResponse({"success": False}, status=400)


@login_required
def change_password(request):
    """Change password view"""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, "Your password was successfully updated!")
            return redirect("customer_portal:dashboard")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "customer_portal/change_password.html", {"form": form})


@login_required
def notification_list(request):
    """List all notifications for the user"""
    notifications = Notification.objects.filter(user=request.user)
    
    # Filter by read status
    filter_status = request.GET.get('status', 'all')
    if filter_status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_status == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Filter by type
    filter_type = request.GET.get('type')
    if filter_type and filter_type != 'all':
        notifications = notifications.filter(notification_type=filter_type)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unread count
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'notifications': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'unread_count': unread_count,
        'filter_status': filter_status,
        'filter_type': filter_type,
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    
    return render(request, 'customer_portal/notification_list.html', context)


@login_required
def notification_detail(request, pk):
    """View a single notification and mark it as read"""
    notification = get_object_or_404(Notification, user=request.user, pk=pk)
    
    # Mark as read
    notification.mark_as_read()
    
    # If notification has a link, redirect to it
    if notification.link:
        return redirect(notification.link)
    
    return render(request, 'customer_portal/notification_detail.html', {
        'notification': notification
    })


@login_required
def mark_notification_read(request, pk):
    """Mark a notification as read via AJAX"""
    if request.method == 'POST':
        notification = get_object_or_404(Notification, user=request.user, pk=pk)
        notification.mark_as_read()
        
        # Get updated unread count
        unread_count = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count
        })
    
    return JsonResponse({'success': False}, status=400)


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    if request.method == 'POST':
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        messages.success(request, 'All notifications marked as read.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect('customer_portal:notification_list')
    
    return JsonResponse({'success': False}, status=400)


@login_required
def get_notification_count(request):
    """Get unread notification count via AJAX"""
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({'unread_count': unread_count})


# Organization features removed - only for admin/staff use
# These views are commented out as organizations are managed only by admin/staff
# through the dashboard, not by customers through the portal

"""
@login_required
def organization_view(request):
    # View and manage organization details
    try:
        customer = request.user.customer
    except Customer.DoesNotExist:
        messages.warning(request, "Please complete your profile first.")
        return redirect('customer_portal:profile')
    
    if not customer.organization:
        # If no organization, offer to create one
        return render(request, 'customer_portal/organization_create_prompt.html', {
            'customer': customer
        })
    
    organization = customer.organization
    
    # Check if user has permission to manage organization
    if not customer.can_manage_organization():
        # Regular members can only view
        members = organization.customers.filter(is_active=True).order_by('role', 'last_name')
        return render(request, 'customer_portal/organization_view.html', {
            'organization': organization,
            'customer': customer,
            'members': members,
            'can_manage': False
        })
    
    # Admin/Owner can edit
    if request.method == 'POST':
        # Update organization details
        organization.name = request.POST.get('name', organization.name)
        organization.organization_type = request.POST.get('organization_type', organization.organization_type)
        organization.tax_id = request.POST.get('tax_id', '')
        organization.website = request.POST.get('website', '')
        organization.email = request.POST.get('email', '')
        organization.phone = request.POST.get('phone', '')
        organization.address_line1 = request.POST.get('address_line1', '')
        organization.address_line2 = request.POST.get('address_line2', '')
        organization.city = request.POST.get('city', '')
        organization.state = request.POST.get('state', '')
        organization.postal_code = request.POST.get('postal_code', '')
        organization.country = request.POST.get('country', 'United States')
        organization.notes = request.POST.get('notes', '')
        
        organization.save()
        messages.success(request, 'Organization details updated successfully!')
        return redirect('customer_portal:organization')
    
    members = organization.customers.filter(is_active=True).order_by('role', 'last_name')
    
    return render(request, 'customer_portal/organization_edit.html', {
        'organization': organization,
        'customer': customer,
        'members': members,
        'can_manage': True,
        'organization_types': Organization.ORGANIZATION_TYPE_CHOICES
    })


@login_required
def organization_create(request):
    # Create a new organization
    try:
        customer = request.user.customer
    except Customer.DoesNotExist:
        messages.warning(request, "Please complete your profile first.")
        return redirect('customer_portal:profile')
    
    if customer.organization:
        messages.info(request, "You already belong to an organization.")
        return redirect('customer_portal:organization')
    
    if request.method == 'POST':
        # Create new organization
        organization = Organization(
            name=request.POST.get('name'),
            organization_type=request.POST.get('organization_type', 'dental_practice'),
            tax_id=request.POST.get('tax_id', ''),
            website=request.POST.get('website', ''),
            email=request.POST.get('email', ''),
            phone=request.POST.get('phone', ''),
            address_line1=request.POST.get('address_line1', ''),
            address_line2=request.POST.get('address_line2', ''),
            city=request.POST.get('city', ''),
            state=request.POST.get('state', ''),
            postal_code=request.POST.get('postal_code', ''),
            country=request.POST.get('country', 'United States'),
            notes=request.POST.get('notes', ''),
            is_active=True
        )
        organization.save()
        
        # Link customer to organization as owner
        customer.organization = organization
        customer.role = 'owner'
        customer.save()
        
        messages.success(request, f'Organization "{organization.name}" created successfully!')
        return redirect('customer_portal:organization')
    
    return render(request, 'customer_portal/organization_create.html', {
        'customer': customer,
        'organization_types': Organization.ORGANIZATION_TYPE_CHOICES
    })


@login_required
def organization_invite(request):
    # Invite users to join organization
    try:
        customer = request.user.customer
    except Customer.DoesNotExist:
        messages.warning(request, "Please complete your profile first.")
        return redirect('customer_portal:profile')
    
    if not customer.organization or not customer.can_manage_organization():
        messages.error(request, "You don't have permission to invite users.")
        return redirect('customer_portal:organization')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        role = request.POST.get('role', 'staff')
        
        # Check if user with this email exists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(email=email)
            # Check if user already has a customer profile
            if hasattr(user, 'customer'):
                if user.customer.organization:
                    messages.warning(request, f"User {email} already belongs to an organization.")
                else:
                    # Add user to organization
                    user.customer.organization = customer.organization
                    user.customer.role = role
                    user.customer.save()
                    messages.success(request, f"User {email} added to organization successfully!")
            else:
                # Create customer profile and add to organization
                Customer.objects.create(
                    user=user,
                    email=user.email,
                    first_name=user.first_name or '',
                    last_name=user.last_name or '',
                    organization=customer.organization,
                    role=role,
                    is_active=True
                )
                messages.success(request, f"User {email} added to organization successfully!")
        except User.DoesNotExist:
            # Send invitation email (placeholder for now)
            messages.info(request, f"Invitation sent to {email}. They will be added when they sign up.")
        
        return redirect('customer_portal:organization')
    
    return render(request, 'customer_portal/organization_invite.html', {
        'customer': customer,
        'organization': customer.organization,
        'role_choices': Customer.ROLE_CHOICES
    })


@login_required
def organization_member_update(request, member_id):
    # Update member role or remove from organization
    try:
        customer = request.user.customer
    except Customer.DoesNotExist:
        messages.warning(request, "Please complete your profile first.")
        return redirect('customer_portal:profile')
    
    if not customer.organization or not customer.can_manage_organization():
        messages.error(request, "You don't have permission to manage members.")
        return redirect('customer_portal:organization')
    
    member = get_object_or_404(Customer, pk=member_id, organization=customer.organization)
    
    # Can't modify self or other owners (unless you're the only owner)
    if member == customer:
        messages.error(request, "You can't modify your own membership.")
        return redirect('customer_portal:organization')
    
    if member.role == 'owner':
        owner_count = customer.organization.customers.filter(role='owner').count()
        if owner_count <= 1:
            messages.error(request, "Can't modify the only owner.")
            return redirect('customer_portal:organization')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_role':
            new_role = request.POST.get('role')
            member.role = new_role
            member.save()
            messages.success(request, f"Updated {member.get_full_name()}'s role to {member.get_role_display()}.")
        
        elif action == 'remove':
            member.organization = None
            member.role = 'customer'
            member.save()
            messages.success(request, f"Removed {member.get_full_name()} from organization.")
        
        return redirect('customer_portal:organization')
    
    return render(request, 'customer_portal/organization_member_update.html', {
        'customer': customer,
        'organization': customer.organization,
        'member': member,
        'role_choices': Customer.ROLE_CHOICES
    })
"""
