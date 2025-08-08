from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
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


class AddressListView(LoginRequiredMixin, ListView):
    model = CustomerAddress
    template_name = 'customer/address_list.html'
    context_object_name = 'addresses'
    paginate_by = 10
    
    def get_queryset(self):
        # Get or create customer profile for the logged-in user
        customer, created = Customer.objects.get_or_create(
            user=self.request.user,
            defaults={
                'email': self.request.user.email,
                'first_name': self.request.user.first_name or 'First',
                'last_name': self.request.user.last_name or 'Last'
            }
        )
        # Return only active addresses for this customer
        return CustomerAddress.objects.filter(
            customer=customer,
            is_active=True
        ).order_by('-is_default', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = Customer.objects.get(user=self.request.user)
        context['customer'] = customer
        
        # Group addresses by type for display
        addresses = self.get_queryset()
        context['billing_addresses'] = addresses.filter(
            Q(address_type='billing') | Q(address_type='both')
        )
        context['shipping_addresses'] = addresses.filter(
            Q(address_type='shipping') | Q(address_type='both')
        )
        return context


class AddressCreateView(LoginRequiredMixin, CreateView):
    model = CustomerAddress
    form_class = CustomerAddressForm
    template_name = 'customer/address_form.html'
    success_url = reverse_lazy('customer:address_list')
    
    def form_valid(self, form):
        customer = Customer.objects.get(user=self.request.user)
        form.instance.customer = customer
        messages.success(self.request, 'Address added successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Address'
        context['button_text'] = 'Add Address'
        return context


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomerAddress
    form_class = CustomerAddressForm
    template_name = 'customer/address_form.html'
    success_url = reverse_lazy('customer:address_list')
    
    def get_queryset(self):
        customer = Customer.objects.get(user=self.request.user)
        return CustomerAddress.objects.filter(customer=customer, is_active=True)
    
    def form_valid(self, form):
        messages.success(self.request, 'Address updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Address'
        context['button_text'] = 'Update Address'
        return context


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    model = CustomerAddress
    template_name = 'customer/address_confirm_delete.html'
    success_url = reverse_lazy('customer:address_list')
    
    def get_queryset(self):
        customer = Customer.objects.get(user=self.request.user)
        return CustomerAddress.objects.filter(customer=customer, is_active=True)
    
    def delete(self, request, *args, **kwargs):
        # Instead of actually deleting, we'll soft delete by setting is_active to False
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        messages.success(request, 'Address removed successfully!')
        return redirect(self.success_url)


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


class CustomerAddressCreateView(LoginRequiredMixin, CreateView):
    """Create a new address for a specific customer"""
    model = CustomerAddress
    form_class = CustomerAddressForm
    template_name = 'customer/customer_address_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.customer = get_object_or_404(Customer, pk=kwargs['customer_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context
    
    def form_valid(self, form):
        form.instance.customer = self.customer
        messages.success(self.request, 'Address added successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('customer:customer_detail', kwargs={'pk': self.customer.pk}) + '?tab=addresses'


# Customer views
class CustomerListView(StaffRequiredMixin, ListView):
    model = Customer
    template_name = 'customer/customer_list_daisyui.html'  # Use DaisyUI template
    context_object_name = 'customers'
    
    def get_paginate_by(self, queryset):
        # Dynamic pagination based on user selection
        rows = self.request.GET.get('rows', '20')
        try:
            paginate_by = int(rows)
            if paginate_by not in [10, 20, 50, 100]:
                paginate_by = 20
        except (ValueError, TypeError):
            paginate_by = 20
        return paginate_by
    
    def get_queryset(self):
        queryset = Customer.objects.filter(is_active=True)
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(company_name__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        
        # Filter by company category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(company_category=category)
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Customer.company_category_choices
        context['selected_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('search', '')
        context['rows_per_page'] = self.get_paginate_by(None)
        return context


class CustomerDetailView(StaffRequiredMixin, DetailView):
    model = Customer
    template_name = 'customer/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        
        # Get related data
        context['contacts'] = customer.contacts.all()
        context['recent_notes'] = customer.notes.all()[:5]
        context['documents'] = customer.documents.all()
        context['addresses'] = customer.addresses.filter(is_active=True)
        
        return context


class CustomerCreateView(StaffRequiredMixin, CreateView):
    """Step 1: Create customer basic information"""
    model = Customer
    form_class = CustomerForm
    template_name = 'customer/customer_create_step1.html'
    
    def get_success_url(self):
        # Redirect to step 2 (add address)
        return reverse('customer:customer_create_step2', kwargs={'customer_pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Customer created successfully! Now add their address.')
        return super().form_valid(form)


class CustomerCreateStep2View(StaffRequiredMixin, CreateView):
    """Step 2: Add customer address"""
    model = CustomerAddress
    form_class = CustomerAddressForm
    template_name = 'customer/customer_create_step2.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.customer = get_object_or_404(Customer, pk=kwargs['customer_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        context['step'] = 2
        return context
    
    def form_valid(self, form):
        form.instance.customer = self.customer
        messages.success(self.request, 'Customer address added successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('customer:customer_detail', kwargs={'pk': self.customer.pk})


class CustomerUpdateView(StaffRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customer/customer_form.html'
    
    def get_success_url(self):
        return reverse('customer:customer_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Customer updated successfully!')
        return super().form_valid(form)


class CustomerDeleteView(StaffRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customer/customer_confirm_delete.html'
    success_url = reverse_lazy('customer:customer_list')
    
    def delete(self, request, *args, **kwargs):
        # Soft delete
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        messages.success(request, 'Customer deleted successfully!')
        return redirect(self.success_url)


# CustomerContact views
class ContactListView(LoginRequiredMixin, ListView):
    model = CustomerContact
    template_name = 'customer/contact_list.html'
    context_object_name = 'contacts'
    paginate_by = 20
    
    def get_queryset(self):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return CustomerContact.objects.filter(customer=self.customer)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context


class ContactCreateView(LoginRequiredMixin, CreateView):
    model = CustomerContact
    form_class = CustomerContactForm
    template_name = 'customer/contact_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.customer = self.customer
        messages.success(self.request, 'Contact added successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('customer:customer_detail', kwargs={'pk': self.customer.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        context['title'] = f'Add Contact for {self.customer}'
        return context


class ContactUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomerContact
    form_class = CustomerContactForm
    template_name = 'customer/contact_form.html'
    
    def get_queryset(self):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return CustomerContact.objects.filter(customer=self.customer)
    
    def form_valid(self, form):
        messages.success(self.request, 'Contact updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('customer:customer_detail', kwargs={'pk': self.customer.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        context['title'] = f'Edit Contact for {self.customer}'
        return context


class ContactDeleteView(LoginRequiredMixin, DeleteView):
    model = CustomerContact
    template_name = 'customer/contact_confirm_delete.html'
    
    def get_queryset(self):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return CustomerContact.objects.filter(customer=self.customer)
    
    def get_success_url(self):
        return reverse('customer:customer_detail', kwargs={'pk': self.customer.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Contact deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context


# CustomerNote views
class NoteCreateView(LoginRequiredMixin, CreateView):
    model = CustomerNote
    form_class = CustomerNoteForm
    template_name = 'customer/note_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.customer = self.customer
        messages.success(self.request, 'Note added successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('customer:customer_detail', kwargs={'pk': self.customer.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        context['title'] = f'Add Note for {self.customer}'
        return context


class NoteListView(LoginRequiredMixin, ListView):
    model = CustomerNote
    template_name = 'customer/note_list.html'
    context_object_name = 'notes'
    paginate_by = 20
    
    def get_queryset(self):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return CustomerNote.objects.filter(customer=self.customer)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context


class NoteDeleteView(LoginRequiredMixin, DeleteView):
    model = CustomerNote
    template_name = 'customer/note_confirm_delete.html'
    
    def get_queryset(self):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return CustomerNote.objects.filter(customer=self.customer)
    
    def get_success_url(self):
        return reverse('customer:customer_detail', kwargs={'pk': self.customer.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Note deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context


# CustomerDocument views
class DocumentCreateView(LoginRequiredMixin, CreateView):
    model = CustomerDocument
    form_class = CustomerDocumentForm
    template_name = 'customer/document_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.customer = self.customer
        messages.success(self.request, 'Document uploaded successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('customer:customer_detail', kwargs={'pk': self.customer.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        context['title'] = f'Upload Document for {self.customer}'
        return context


class DocumentListView(LoginRequiredMixin, ListView):
    model = CustomerDocument
    template_name = 'customer/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20
    
    def get_queryset(self):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return CustomerDocument.objects.filter(customer=self.customer)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = CustomerDocument
    template_name = 'customer/document_confirm_delete.html'
    
    def get_queryset(self):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['customer_pk'])
        return CustomerDocument.objects.filter(customer=self.customer)
    
    def get_success_url(self):
        return reverse('customer:customer_detail', kwargs={'pk': self.customer.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Document deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context


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