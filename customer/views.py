from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from .models import Customer, CustomerAddress, CustomerContact, CustomerNote, CustomerDocument, Organization
from .forms import CustomerAddressForm, CustomerForm, CustomerContactForm, CustomerNoteForm, CustomerDocumentForm


# Custom decorator for admin-only access
def admin_required(view_func):
    """Decorator to ensure user is a superuser (admin)"""
    decorated_view_func = user_passes_test(
        lambda u: u.is_active and u.is_superuser,
        login_url='/accounts/login/',
        redirect_field_name='next'
    )(view_func)
    return decorated_view_func


# Staff Required Mixin for all admin views
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to ensure user is staff"""
    def test_func(self):
        return self.request.user.is_staff


@login_required
def address_list(request):
    """List all addresses for the logged-in user"""
    # Get or create customer profile for the logged-in user
    customer, created = Customer.objects.get_or_create(
        user=request.user,
        defaults={
            'email': request.user.email,
            'first_name': request.user.first_name or 'First',
            'last_name': request.user.last_name or 'Last'
        }
    )
    
    # Get only active addresses for this customer
    addresses = CustomerAddress.objects.filter(
        customer=customer,
        is_active=True
    ).order_by('-is_default', '-created_at')
    
    # Pagination
    paginator = Paginator(addresses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Group addresses by type for display
    billing_addresses = addresses.filter(
        Q(address_type='billing') | Q(address_type='both')
    )
    shipping_addresses = addresses.filter(
        Q(address_type='shipping') | Q(address_type='both')
    )
    
    context = {
        'addresses': page_obj,
        'page_obj': page_obj,
        'customer': customer,
        'billing_addresses': billing_addresses,
        'shipping_addresses': shipping_addresses,
    }
    
    return render(request, 'customer/address_list.html', context)


@login_required
def address_create(request):
    """Create a new address for the logged-in user"""
    customer = Customer.objects.get(user=request.user)
    
    if request.method == 'POST':
        form = CustomerAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.customer = customer
            address.save()
            messages.success(request, 'Address added successfully!')
            return redirect('customer:address_list')
    else:
        form = CustomerAddressForm()
    
    context = {
        'form': form,
        'title': 'Add New Address',
        'button_text': 'Add Address',
    }
    
    return render(request, 'customer/address_form.html', context)


@login_required
def address_update(request, pk):
    """Update an existing address for the logged-in user"""
    customer = Customer.objects.get(user=request.user)
    address = get_object_or_404(CustomerAddress, pk=pk, customer=customer, is_active=True)
    
    if request.method == 'POST':
        form = CustomerAddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('customer:address_list')
    else:
        form = CustomerAddressForm(instance=address)
    
    context = {
        'form': form,
        'title': 'Edit Address',
        'button_text': 'Update Address',
    }
    
    return render(request, 'customer/address_form.html', context)


@login_required
def address_delete(request, pk):
    """Delete an address (soft delete) for the logged-in user"""
    customer = Customer.objects.get(user=request.user)
    address = get_object_or_404(CustomerAddress, pk=pk, customer=customer, is_active=True)
    
    if request.method == 'POST':
        # Soft delete by setting is_active to False
        address.is_active = False
        address.save()
        messages.success(request, 'Address removed successfully!')
        return redirect('customer:address_list')
    
    context = {
        'address': address,
    }
    
    return render(request, 'customer/address_confirm_delete.html', context)


@login_required
def set_default_address(request, pk):
    """Set an address as default for its type"""
    customer = Customer.objects.get(user=request.user)
    address = get_object_or_404(CustomerAddress, pk=pk, customer=customer, is_active=True)
    
    # Set this address as default (the model's save method handles unsetting others)
    address.is_default = True
    address.save()
    
    messages.success(request, f'Default {address.get_address_type_display().lower()} set successfully!')
    return redirect('customer:address_list')


@login_required
def customer_address_create(request, customer_pk):
    """Create a new address for a specific customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    
    if request.method == 'POST':
        form = CustomerAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.customer = customer
            address.save()
            messages.success(request, 'Address added successfully!')
            return redirect('customer:customer_detail', pk=customer.pk)
    else:
        form = CustomerAddressForm()
    
    context = {
        'form': form,
        'customer': customer,
    }
    
    return render(request, 'customer/customer_address_form.html', context)


# Customer views - converted from class-based to function-based
@staff_member_required
def customer_list(request):
    """List all customers"""
    queryset = Customer.objects.filter(is_active=True)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        queryset = queryset.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(company_name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    # Filter by company category
    category = request.GET.get('category', '')
    if category:
        queryset = queryset.filter(company_category=category)
    
    queryset = queryset.order_by('-date_joined')
    
    # Dynamic pagination based on user selection
    rows = request.GET.get('rows', '20')
    try:
        paginate_by = int(rows)
        if paginate_by not in [10, 20, 50, 100]:
            paginate_by = 20
    except (ValueError, TypeError):
        paginate_by = 20
    
    paginator = Paginator(queryset, paginate_by)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'customers': page_obj,
        'page_obj': page_obj,
        'categories': Customer.company_category_choices,
        'selected_category': category,
        'search_query': search_query,
        'rows_per_page': paginate_by,
    }
    
    return render(request, 'customer/customer_list_daisyui.html', context)


@staff_member_required
def customer_detail(request, pk):
    """Display customer details"""
    customer = get_object_or_404(Customer, pk=pk)
    
    context = {
        'customer': customer,
        'contacts': customer.contacts.all(),
        'recent_notes': customer.notes.all()[:5],
        'documents': customer.documents.all(),
        'addresses': customer.addresses.filter(is_active=True),
    }
    
    return render(request, 'customer/customer_detail.html', context)


@staff_member_required
def customer_create(request):
    """Create a new customer"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, 'Customer created successfully! Now add their address.')
            # Redirect to step 2 (add address)
            return redirect('customer:customer_create_step2', customer_pk=customer.pk)
    else:
        form = CustomerForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'customer/customer_create_step1.html', context)


@staff_member_required
def customer_create_step2(request, customer_pk):
    """Step 2: Add customer address"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    
    if request.method == 'POST':
        form = CustomerAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.customer = customer
            address.save()
            messages.success(request, 'Customer address added successfully!')
            return redirect('customer:customer_detail', pk=customer.pk)
    else:
        form = CustomerAddressForm()
    
    context = {
        'form': form,
        'customer': customer,
        'step': 2,
    }
    
    return render(request, 'customer/customer_create_step2.html', context)


@staff_member_required
def customer_update(request, pk):
    """Update an existing customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated successfully!')
            return redirect('customer:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'form': form,
        'customer': customer,
    }
    
    return render(request, 'customer/customer_form.html', context)


@staff_member_required
def customer_delete(request, pk):
    """Delete a customer (soft delete)"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        # Soft delete
        customer.is_active = False
        customer.save()
        messages.success(request, 'Customer deleted successfully!')
        return redirect('customer:customer_list')
    
    context = {
        'customer': customer,
    }
    
    return render(request, 'customer/customer_confirm_delete.html', context)


# CustomerContact views
@login_required
def contact_list(request, customer_pk):
    """List all contacts for a customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    contacts = CustomerContact.objects.filter(customer=customer)
    
    # Pagination
    paginator = Paginator(contacts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'contacts': page_obj,
        'page_obj': page_obj,
        'customer': customer,
    }
    
    return render(request, 'customer/contact_list.html', context)


@login_required
def contact_create(request, customer_pk):
    """Create a new contact for a customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    
    if request.method == 'POST':
        form = CustomerContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.customer = customer
            contact.save()
            messages.success(request, 'Contact added successfully!')
            return redirect('customer:customer_detail', pk=customer.pk)
    else:
        form = CustomerContactForm()
    
    context = {
        'form': form,
        'customer': customer,
        'title': f'Add Contact for {customer}',
    }
    
    return render(request, 'customer/contact_form.html', context)


@login_required
def contact_update(request, customer_pk, pk):
    """Update an existing contact for a customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    contact = get_object_or_404(CustomerContact, pk=pk, customer=customer)
    
    if request.method == 'POST':
        form = CustomerContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contact updated successfully!')
            return redirect('customer:customer_detail', pk=customer.pk)
    else:
        form = CustomerContactForm(instance=contact)
    
    context = {
        'form': form,
        'customer': customer,
        'title': f'Edit Contact for {customer}',
    }
    
    return render(request, 'customer/contact_form.html', context)


@login_required
def contact_delete(request, customer_pk, pk):
    """Delete a contact for a customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    contact = get_object_or_404(CustomerContact, pk=pk, customer=customer)
    
    if request.method == 'POST':
        contact.delete()
        messages.success(request, 'Contact deleted successfully!')
        return redirect('customer:customer_detail', pk=customer.pk)
    
    context = {
        'contact': contact,
        'customer': customer,
    }
    
    return render(request, 'customer/contact_confirm_delete.html', context)


# CustomerNote views
@login_required
def note_create(request, customer_pk):
    """Create a new note for a customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    
    if request.method == 'POST':
        form = CustomerNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.customer = customer
            note.save()
            messages.success(request, 'Note added successfully!')
            return redirect('customer:customer_detail', pk=customer.pk)
    else:
        form = CustomerNoteForm()
    
    context = {
        'form': form,
        'customer': customer,
        'title': f'Add Note for {customer}',
    }
    
    return render(request, 'customer/note_form.html', context)


@login_required
def note_list(request, customer_pk):
    """List all notes for a customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    notes = CustomerNote.objects.filter(customer=customer)
    
    # Pagination
    paginator = Paginator(notes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'notes': page_obj,
        'page_obj': page_obj,
        'customer': customer,
    }
    
    return render(request, 'customer/note_list.html', context)


@login_required
def note_delete(request, customer_pk, pk):
    """Delete a note for a customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    note = get_object_or_404(CustomerNote, pk=pk, customer=customer)
    
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted successfully!')
        return redirect('customer:customer_detail', pk=customer.pk)
    
    context = {
        'note': note,
        'customer': customer,
    }
    
    return render(request, 'customer/note_confirm_delete.html', context)


# CustomerDocument views
@login_required
def document_create(request, customer_pk):
    """Upload a new document for a customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    
    if request.method == 'POST':
        form = CustomerDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.customer = customer
            document.save()
            messages.success(request, 'Document uploaded successfully!')
            return redirect('customer:customer_detail', pk=customer.pk)
    else:
        form = CustomerDocumentForm()
    
    context = {
        'form': form,
        'customer': customer,
        'title': f'Upload Document for {customer}',
    }
    
    return render(request, 'customer/document_form.html', context)


@login_required
def document_list(request, customer_pk):
    """List all documents for a customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    documents = CustomerDocument.objects.filter(customer=customer)
    
    # Pagination
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'documents': page_obj,
        'page_obj': page_obj,
        'customer': customer,
    }
    
    return render(request, 'customer/document_list.html', context)


@login_required
def document_delete(request, customer_pk, pk):
    """Delete a document for a customer"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    document = get_object_or_404(CustomerDocument, pk=pk, customer=customer)
    
    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Document deleted successfully!')
        return redirect('customer:customer_detail', pk=customer.pk)
    
    context = {
        'document': document,
        'customer': customer,
    }
    
    return render(request, 'customer/document_confirm_delete.html', context)


# AJAX views for quick actions
@login_required
def toggle_contact_primary(request, customer_pk, pk):
    if request.method == 'POST':
        customer = get_object_or_404(Customer, pk=customer_pk)
        contact = get_object_or_404(CustomerContact, pk=pk, customer=customer)
        
        # If setting as primary, unset other primary contacts
        if not contact.is_primary:
            CustomerContact.objects.filter(customer=customer, is_primary=True).update(is_primary=False)
            contact.is_primary = True
        else:
            contact.is_primary = False
        
        contact.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'is_primary': contact.is_primary})
        
        messages.success(request, 'Contact updated successfully!')
        return redirect('customer:customer_detail', pk=customer.pk)
    
    return HttpResponseForbidden()


# My Organization View for Admin Users
@admin_required
def my_organization(request):
    """View or create current user's organization"""
    if request.user.organization:
        return redirect('customer:organization_detail', pk=request.user.organization.pk)
    
    # No organization - show create form
    if request.method == 'POST':
        # Create new organization and assign to user
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
        
        # Assign the organization to the current user
        request.user.organization = organization
        request.user.save()
        
        messages.success(request, f'Organization "{organization.name}" created successfully and assigned to you!')
        return redirect('customer:organization_detail', pk=organization.pk)
    
    # Show create organization form
    context = {
        'organization_types': Organization.ORGANIZATION_TYPE_CHOICES,
        'user': request.user,
    }
    
    return render(request, 'customer/my_organization_create.html', context)


# Organization Management Views for Admin
@admin_required
def organization_list(request):
    """List all organizations for admin users"""
    organizations = Organization.objects.all().order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        organizations = organizations.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(tax_id__icontains=search_query)
        )
    
    # Filter by type
    org_type = request.GET.get('type', '')
    if org_type:
        organizations = organizations.filter(organization_type=org_type)
    
    # Filter by active status
    status = request.GET.get('status', '')
    if status == 'active':
        organizations = organizations.filter(is_active=True)
    elif status == 'inactive':
        organizations = organizations.filter(is_active=False)
    
    context = {
        'organizations': organizations,
        'search_query': search_query,
        'selected_type': org_type,
        'selected_status': status,
        'organization_types': Organization.ORGANIZATION_TYPE_CHOICES,
    }
    
    return render(request, 'customer/organization_list.html', context)


@admin_required
def organization_detail(request, pk):
    """View organization details for admin users"""
    organization = get_object_or_404(Organization, pk=pk)
    members = organization.users.all().order_by('last_name', 'first_name')
    
    context = {
        'organization': organization,
        'members': members,
    }
    
    return render(request, 'customer/organization_detail.html', context)


@admin_required
def organization_create(request):
    """Create new organization for admin users"""
    if request.method == 'POST':
        # Get form data
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
            is_active=request.POST.get('is_active') == 'on'
        )
        organization.save()
        
        messages.success(request, f'Organization "{organization.name}" created successfully!')
        return redirect('customer:organization_detail', pk=organization.pk)
    
    context = {
        'organization_types': Organization.ORGANIZATION_TYPE_CHOICES,
    }
    
    return render(request, 'customer/organization_form.html', context)


@admin_required
def organization_update(request, pk):
    """Update organization for admin users"""
    organization = get_object_or_404(Organization, pk=pk)
    
    if request.method == 'POST':
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
        organization.is_active = request.POST.get('is_active') == 'on'
        
        organization.save()
        
        messages.success(request, f'Organization "{organization.name}" updated successfully!')
        return redirect('customer:organization_detail', pk=organization.pk)
    
    context = {
        'organization': organization,
        'organization_types': Organization.ORGANIZATION_TYPE_CHOICES,
    }
    
    return render(request, 'customer/organization_form.html', context)


@admin_required
def organization_delete(request, pk):
    """Delete organization for admin users"""
    organization = get_object_or_404(Organization, pk=pk)
    
    if request.method == 'POST':
        org_name = organization.name
        # Remove all customers from organization before deleting
        organization.customers.update(organization=None, role='customer')
        organization.delete()
        
        messages.success(request, f'Organization "{org_name}" deleted successfully!')
        return redirect('customer:organization_list')
    
    context = {
        'organization': organization,
        'member_count': organization.customers.count(),
    }
    
    return render(request, 'customer/organization_confirm_delete.html', context)


@admin_required
def organization_add_member(request, pk):
    """Add member to organization for admin users"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    organization = get_object_or_404(Organization, pk=pk)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        
        user = get_object_or_404(User, pk=user_id)
        
        # Check if user already belongs to another organization
        if user.organization and user.organization != organization:
            messages.warning(request, f'{user.get_full_name() or user.email} already belongs to {user.organization.name}')
        else:
            user.organization = organization
            user.save()
            
            messages.success(request, f'{user.get_full_name() or user.email} added to organization successfully!')
        
        return redirect('customer:organization_detail', pk=organization.pk)
    
    # Get users without organization for selection (only admins/staff)
    available_users = User.objects.filter(organization__isnull=True, is_superuser=True)
    
    context = {
        'organization': organization,
        'available_users': available_users,
    }
    
    return render(request, 'customer/organization_add_member.html', context)


@admin_required
def organization_remove_member(request, pk, user_id):
    """Remove member from organization for admin users"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    organization = get_object_or_404(Organization, pk=pk)
    user = get_object_or_404(User, pk=user_id, organization=organization)
    
    if request.method == 'POST':
        user_name = user.get_full_name() or user.email
        user.organization = None
        user.save()
        
        messages.success(request, f'{user_name} removed from organization.')
        return redirect('customer:organization_detail', pk=organization.pk)
    
    context = {
        'organization': organization,
        'user': user,
    }
    
    return render(request, 'customer/organization_remove_member.html', context)