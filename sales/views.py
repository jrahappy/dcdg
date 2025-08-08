from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.template.loader import get_template
from decimal import Decimal
import random
from xhtml2pdf import pisa
from io import BytesIO
from .models import Quote, QuoteItem, Order, OrderItem, Invoice, InvoiceItem, Payment
from customer.models import Customer
from product.models import Product, Inventory
from .forms import (
    QuoteForm, QuoteItemFormSet, OrderForm, OrderItemFormSet,
    InvoiceForm, InvoiceItemFormSet, PaymentForm
)


# Staff Required Mixin for all admin views
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to ensure user is staff"""
    def test_func(self):
        return self.request.user.is_staff


# Quote Views
class QuoteListView(StaffRequiredMixin, ListView):
    model = Quote
    template_name = 'sales/quote_list_daisyui.html'
    context_object_name = 'quotes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if search:
            queryset = queryset.filter(
                Q(quote_number__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(customer__company_name__icontains=search)
            )
        
        if status:
            queryset = queryset.filter(status=status)
        
        if date_from:
            queryset = queryset.filter(quote_date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(quote_date__lte=date_to)
        
        return queryset.order_by('-quote_date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['status_choices'] = Quote.STATUS_CHOICES
        
        # Add statistics
        from django.db.models import Sum
        context['total_quotes'] = Quote.objects.count()
        context['draft_count'] = Quote.objects.filter(status='draft').count()
        context['sent_count'] = Quote.objects.filter(status='sent').count()
        context['accepted_count'] = Quote.objects.filter(status='accepted').count()
        context['total_value'] = Quote.objects.filter(status='accepted').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        return context


class QuoteDetailView(StaffRequiredMixin, DetailView):
    model = Quote
    template_name = 'sales/quote_detail.html'
    context_object_name = 'quote'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        return context


class QuoteCreateView(StaffRequiredMixin, CreateView):
    model = Quote
    form_class = QuoteForm
    template_name = 'sales/quote_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = QuoteItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = QuoteItemFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            form.instance.created_by = self.request.user
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            
            # Calculate totals
            self.calculate_quote_totals()
            
            messages.success(self.request, 'Quote created successfully!')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
    
    def calculate_quote_totals(self):
        items = self.object.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (self.object.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (self.object.tax_rate / 100)
        total = subtotal_after_discount + tax_amount
        
        self.object.subtotal = subtotal
        self.object.discount_amount = discount_amount
        self.object.tax_amount = tax_amount
        self.object.total_amount = total
        self.object.save()
    
    def get_success_url(self):
        return reverse('sales:quote_detail', kwargs={'pk': self.object.pk})


class QuoteUpdateView(StaffRequiredMixin, UpdateView):
    model = Quote
    form_class = QuoteForm
    template_name = 'sales/quote_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = QuoteItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = QuoteItemFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            
            # Recalculate totals
            self.calculate_quote_totals()
            
            messages.success(self.request, 'Quote updated successfully!')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
    
    def calculate_quote_totals(self):
        items = self.object.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (self.object.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (self.object.tax_rate / 100)
        total = subtotal_after_discount + tax_amount
        
        self.object.subtotal = subtotal
        self.object.discount_amount = discount_amount
        self.object.tax_amount = tax_amount
        self.object.total_amount = total
        self.object.save()
    
    def get_success_url(self):
        return reverse('sales:quote_detail', kwargs={'pk': self.object.pk})


class QuoteDeleteView(StaffRequiredMixin, DeleteView):
    model = Quote
    template_name = 'sales/quote_confirm_delete.html'
    success_url = reverse_lazy('sales:quote_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Quote deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Quote Item Views
class QuoteItemCreateView(StaffRequiredMixin, CreateView):
    model = QuoteItem
    fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent']
    template_name = 'sales/quote_item_form.html'
    
    def form_valid(self, form):
        quote = get_object_or_404(Quote, pk=self.kwargs['quote_pk'])
        form.instance.quote = quote
        response = super().form_valid(form)
        
        # Recalculate quote totals
        self.recalculate_quote_totals(quote)
        
        messages.success(self.request, 'Item added successfully!')
        return response
    
    def recalculate_quote_totals(self, quote):
        items = quote.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (quote.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (quote.tax_rate / 100)
        total = subtotal_after_discount + tax_amount
        
        quote.subtotal = subtotal
        quote.discount_amount = discount_amount
        quote.tax_amount = tax_amount
        quote.total_amount = total
        quote.save()
    
    def get_success_url(self):
        return reverse('sales:quote_detail', kwargs={'pk': self.kwargs['quote_pk']})


class QuoteItemUpdateView(StaffRequiredMixin, UpdateView):
    model = QuoteItem
    fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent']
    template_name = 'sales/quote_item_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Recalculate quote totals
        self.recalculate_quote_totals(self.object.quote)
        
        messages.success(self.request, 'Item updated successfully!')
        return response
    
    def recalculate_quote_totals(self, quote):
        items = quote.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (quote.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (quote.tax_rate / 100)
        total = subtotal_after_discount + tax_amount
        
        quote.subtotal = subtotal
        quote.discount_amount = discount_amount
        quote.tax_amount = tax_amount
        quote.total_amount = total
        quote.save()
    
    def get_success_url(self):
        return reverse('sales:quote_detail', kwargs={'pk': self.object.quote.pk})


class QuoteItemDeleteView(StaffRequiredMixin, DeleteView):
    model = QuoteItem
    template_name = 'sales/quote_item_confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        quote = self.object.quote
        response = super().delete(request, *args, **kwargs)
        
        # Recalculate quote totals
        self.recalculate_quote_totals(quote)
        
        messages.success(request, 'Item removed successfully!')
        return response
    
    def recalculate_quote_totals(self, quote):
        items = quote.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (quote.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (quote.tax_rate / 100)
        total = subtotal_after_discount + tax_amount
        
        quote.subtotal = subtotal
        quote.discount_amount = discount_amount
        quote.tax_amount = tax_amount
        quote.total_amount = total
        quote.save()
    
    def get_success_url(self):
        return reverse('sales:quote_detail', kwargs={'pk': self.kwargs['quote_pk']})


# Order Views
class OrderListView(StaffRequiredMixin, ListView):
    model = Order
    template_name = 'sales/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        payment_status = self.request.GET.get('payment_status')
        
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(customer__company_name__icontains=search) |
                Q(purchase_order_number__icontains=search)
            )
        
        if status:
            queryset = queryset.filter(status=status)
        
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        return queryset.order_by('-order_date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_payment_status'] = self.request.GET.get('payment_status', '')
        context['status_choices'] = Order.STATUS_CHOICES
        context['payment_status_choices'] = Order.PAYMENT_STATUS_CHOICES
        return context


class OrderDetailView(StaffRequiredMixin, DetailView):
    model = Order
    template_name = 'sales/order_detail.html'
    context_object_name = 'order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        context['payments'] = self.object.payments.all()
        return context


class OrderCreateView(StaffRequiredMixin, CreateView):
    model = Order
    form_class = OrderForm
    template_name = 'sales/order_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = OrderItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = OrderItemFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            form.instance.created_by = self.request.user
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            
            # Calculate totals
            self.calculate_order_totals()
            
            messages.success(self.request, 'Order created successfully!')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
    
    def calculate_order_totals(self):
        items = self.object.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (self.object.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (self.object.tax_rate / 100)
        total = subtotal_after_discount + tax_amount + self.object.shipping_cost
        
        self.object.subtotal = subtotal
        self.object.discount_amount = discount_amount
        self.object.tax_amount = tax_amount
        self.object.total_amount = total
        self.object.balance_due = total - self.object.paid_amount
        self.object.save()
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.object.pk})


class OrderUpdateView(StaffRequiredMixin, UpdateView):
    model = Order
    form_class = OrderForm
    template_name = 'sales/order_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = OrderItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = OrderItemFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            
            # Recalculate totals
            self.calculate_order_totals()
            
            messages.success(self.request, 'Order updated successfully!')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
    
    def calculate_order_totals(self):
        items = self.object.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (self.object.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (self.object.tax_rate / 100)
        total = subtotal_after_discount + tax_amount + self.object.shipping_cost
        
        self.object.subtotal = subtotal
        self.object.discount_amount = discount_amount
        self.object.tax_amount = tax_amount
        self.object.total_amount = total
        self.object.balance_due = total - self.object.paid_amount
        self.object.save()
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.object.pk})


class OrderDeleteView(StaffRequiredMixin, DeleteView):
    model = Order
    template_name = 'sales/order_confirm_delete.html'
    success_url = reverse_lazy('sales:order_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Order deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Order Item Views
class OrderItemCreateView(StaffRequiredMixin, CreateView):
    model = OrderItem
    fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent']
    template_name = 'sales/order_item_form.html'
    
    def form_valid(self, form):
        order = get_object_or_404(Order, pk=self.kwargs['order_pk'])
        form.instance.order = order
        response = super().form_valid(form)
        
        # Recalculate order totals
        self.recalculate_order_totals(order)
        
        messages.success(self.request, 'Item added successfully!')
        return response
    
    def recalculate_order_totals(self, order):
        items = order.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (order.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (order.tax_rate / 100)
        total = subtotal_after_discount + tax_amount + order.shipping_cost
        
        order.subtotal = subtotal
        order.discount_amount = discount_amount
        order.tax_amount = tax_amount
        order.total_amount = total
        order.balance_due = total - order.paid_amount
        order.save()
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.kwargs['order_pk']})


class OrderItemUpdateView(StaffRequiredMixin, UpdateView):
    model = OrderItem
    fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent']
    template_name = 'sales/order_item_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Recalculate order totals
        self.recalculate_order_totals(self.object.order)
        
        messages.success(self.request, 'Item updated successfully!')
        return response
    
    def recalculate_order_totals(self, order):
        items = order.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (order.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (order.tax_rate / 100)
        total = subtotal_after_discount + tax_amount + order.shipping_cost
        
        order.subtotal = subtotal
        order.discount_amount = discount_amount
        order.tax_amount = tax_amount
        order.total_amount = total
        order.balance_due = total - order.paid_amount
        order.save()
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.object.order.pk})


class OrderItemDeleteView(StaffRequiredMixin, DeleteView):
    model = OrderItem
    template_name = 'sales/order_item_confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        order = self.object.order
        response = super().delete(request, *args, **kwargs)
        
        # Recalculate order totals
        self.recalculate_order_totals(order)
        
        messages.success(request, 'Item removed successfully!')
        return response
    
    def recalculate_order_totals(self, order):
        items = order.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (order.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (order.tax_rate / 100)
        total = subtotal_after_discount + tax_amount + order.shipping_cost
        
        order.subtotal = subtotal
        order.discount_amount = discount_amount
        order.tax_amount = tax_amount
        order.total_amount = total
        order.balance_due = total - order.paid_amount
        order.save()
    
    def get_success_url(self):
        return reverse('sales:order_detail', kwargs={'pk': self.kwargs['order_pk']})


# Invoice Views
# Multi-step Invoice Creation Views
class InvoiceCreateStep1View(StaffRequiredMixin, TemplateView):
    template_name = 'sales/invoice_create_step1_daisyui.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.filter(is_active=True).order_by('first_name', 'last_name')
        return context
    
    def post(self, request, *args, **kwargs):
        customer_id = request.POST.get('customer_id')
        if customer_id:
            # Store in session
            request.session['invoice_customer_id'] = customer_id
            return redirect('sales:invoice_create_step2')
        else:
            messages.error(request, 'Please select a customer')
            return redirect('sales:invoice_create_step1')


class InvoiceCreateStep2View(StaffRequiredMixin, TemplateView):
    template_name = 'sales/invoice_create_step2_daisyui.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if customer is selected
        if 'invoice_customer_id' not in request.session:
            messages.warning(request, 'Please select a customer first')
            return redirect('sales:invoice_create_step1')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer_id = self.request.session.get('invoice_customer_id')
        context['customer'] = get_object_or_404(Customer, pk=customer_id)
        context['products'] = Product.objects.filter(status='active').order_by('name')
        
        # Get items from session
        invoice_items = self.request.session.get('invoice_items', [])
        context['invoice_items'] = invoice_items
        
        # Calculate totals
        subtotal = sum(float(item['line_total']) for item in invoice_items)
        context['subtotal'] = subtotal
        
        return context
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'add_item':
            # Add new item
            product_id = request.POST.get('product_id')
            inventory_id = request.POST.get('inventory_id')
            description = request.POST.get('description')
            quantity = float(request.POST.get('quantity', 1))
            unit_price = float(request.POST.get('unit_price', 0))
            discount_percent = float(request.POST.get('discount_percent', 0))
            
            # Calculate line total
            subtotal = quantity * unit_price
            discount_amount = subtotal * (discount_percent / 100)
            line_total = subtotal - discount_amount
            
            # Get product name and check for serial number management
            product = None
            product_name = ''
            is_serial_managed = False
            if product_id:
                product = Product.objects.get(pk=product_id)
                product_name = product.name
                is_serial_managed = product.is_serial_number_managed
            
            # Validate inventory for serial managed products
            if is_serial_managed and inventory_id:
                inventory = get_object_or_404(Inventory, pk=inventory_id)
                # Check if inventory is available
                if inventory.status != 'available':
                    messages.error(request, f'Inventory item {inventory.serial_number} is not available')
                    return redirect('sales:invoice_create_step2')
                # Update description to include serial number
                description = f"{product_name} (SN: {inventory.serial_number})"
            elif is_serial_managed and not inventory_id:
                messages.error(request, 'Please select an inventory item for serial number managed product')
                return redirect('sales:invoice_create_step2')
            
            # Get or create items list in session
            invoice_items = request.session.get('invoice_items', [])
            
            # Add item
            invoice_items.append({
                'product_id': product_id,
                'product_name': product_name,
                'inventory_id': inventory_id,
                'description': description,
                'quantity': quantity,
                'unit_price': unit_price,
                'discount_percent': discount_percent,
                'line_total': line_total
            })
            
            request.session['invoice_items'] = invoice_items
            messages.success(request, 'Item added successfully')
            
        elif action == 'remove_item':
            # Remove item
            item_index = int(request.POST.get('item_index'))
            invoice_items = request.session.get('invoice_items', [])
            if 0 <= item_index < len(invoice_items):
                removed_item = invoice_items.pop(item_index)
                request.session['invoice_items'] = invoice_items
                messages.success(request, 'Item removed successfully')
            
        elif action == 'next':
            # Proceed to next step
            invoice_items = request.session.get('invoice_items', [])
            if invoice_items:
                return redirect('sales:invoice_create_step3')
            else:
                messages.error(request, 'Please add at least one item')
        
        return redirect('sales:invoice_create_step2')


class InvoiceCreateStep3View(StaffRequiredMixin, TemplateView):
    template_name = 'sales/invoice_create_step3_daisyui.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if customer and items are in session
        if 'invoice_customer_id' not in request.session:
            messages.warning(request, 'Please select a customer first')
            return redirect('sales:invoice_create_step1')
        
        invoice_items = request.session.get('invoice_items', [])
        if not invoice_items:
            messages.warning(request, 'Please add items to the invoice')
            return redirect('sales:invoice_create_step2')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get customer
        customer_id = self.request.session.get('invoice_customer_id')
        context['customer'] = get_object_or_404(Customer, pk=customer_id)
        
        # Get items
        invoice_items = self.request.session.get('invoice_items', [])
        context['invoice_items'] = invoice_items
        
        # Get invoice data from session or defaults
        invoice_data = self.request.session.get('invoice_data', {})
        
        # Calculate totals
        subtotal = sum(float(item['line_total']) for item in invoice_items)
        discount_percent = float(invoice_data.get('discount_percent', 0))
        tax_rate = float(invoice_data.get('tax_rate', 0))
        
        discount_amount = subtotal * (discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        tax_amount = subtotal_after_discount * (tax_rate / 100)
        total_amount = subtotal_after_discount + tax_amount
        
        context['subtotal'] = subtotal
        context['discount_percent'] = discount_percent
        context['discount_amount'] = discount_amount
        context['tax_rate'] = tax_rate
        context['tax_amount'] = tax_amount
        context['total_amount'] = total_amount
        
        # Invoice details
        context['invoice_number'] = invoice_data.get('invoice_number', self._generate_invoice_number())
        context['invoice_date'] = invoice_data.get('invoice_date', timezone.now().date())
        context['due_date'] = invoice_data.get('due_date', (timezone.now() + timezone.timedelta(days=30)).date())
        context['notes'] = invoice_data.get('notes', '')
        
        return context
    
    def _generate_invoice_number(self):
        date = timezone.now()
        year = date.year
        month = str(date.month).zfill(2)
        random_suffix = str(random.randint(100, 999))
        return f"INV-{year}{month}-{random_suffix}"
    
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'update':
            # Update invoice data
            invoice_data = {
                'invoice_number': request.POST.get('invoice_number'),
                'invoice_date': request.POST.get('invoice_date'),
                'due_date': request.POST.get('due_date'),
                'discount_percent': request.POST.get('discount_percent', 0),
                'tax_rate': request.POST.get('tax_rate', 0),
                'notes': request.POST.get('notes', ''),
            }
            request.session['invoice_data'] = invoice_data
            messages.success(request, 'Invoice details updated')
            return redirect('sales:invoice_create_step3')
        
        elif action == 'save':
            # Create the invoice
            customer_id = request.session.get('invoice_customer_id')
            customer = get_object_or_404(Customer, pk=customer_id)
            invoice_items = request.session.get('invoice_items', [])
            invoice_data = request.session.get('invoice_data', {})
            
            # Create invoice
            invoice = Invoice.objects.create(
                customer=customer,
                invoice_number=request.POST.get('invoice_number', self._generate_invoice_number()),
                invoice_date=request.POST.get('invoice_date', timezone.now().date()),
                due_date=request.POST.get('due_date', (timezone.now() + timezone.timedelta(days=30)).date()),
                discount_percent=Decimal(request.POST.get('discount_percent', 0)),
                tax_rate=Decimal(request.POST.get('tax_rate', 0)),
                notes=request.POST.get('notes', ''),
                status='draft',
                billing_address_line1=customer.address_line1,
                billing_address_line2=customer.address_line2,
                billing_city=customer.city,
                billing_state=customer.state,
                billing_postal_code=customer.postal_code,
                billing_country=customer.country,
                created_by=request.user
            )
            
            # Create invoice items
            for item in invoice_items:
                invoice_item = InvoiceItem.objects.create(
                    invoice=invoice,
                    product_id=item['product_id'] if item['product_id'] else None,
                    inventory_id=item.get('inventory_id') if item.get('inventory_id') else None,
                    description=item['description'],
                    quantity=Decimal(str(item['quantity'])),
                    unit_price=Decimal(str(item['unit_price'])),
                    discount_percent=Decimal(str(item['discount_percent']))
                )
                
                # Update inventory status if serial managed item
                if item.get('inventory_id'):
                    inventory = Inventory.objects.get(pk=item['inventory_id'])
                    inventory.status = 'sold'
                    inventory.customer = customer
                    inventory.sale_date = timezone.now().date()
                    inventory.sale_price = Decimal(str(item['unit_price']))
                    inventory.save()
            
            # Calculate totals
            items = invoice.items.all()
            subtotal = sum(item.line_total for item in items)
            
            discount_amount = subtotal * (invoice.discount_percent / Decimal('100'))
            subtotal_after_discount = subtotal - discount_amount
            
            tax_amount = subtotal_after_discount * (invoice.tax_rate / Decimal('100'))
            total = subtotal_after_discount + tax_amount
            
            invoice.subtotal = subtotal
            invoice.discount_amount = discount_amount
            invoice.tax_amount = tax_amount
            invoice.total_amount = total
            invoice.balance_due = total
            invoice.save()
            
            # Clear session
            if 'invoice_customer_id' in request.session:
                del request.session['invoice_customer_id']
            if 'invoice_items' in request.session:
                del request.session['invoice_items']
            if 'invoice_data' in request.session:
                del request.session['invoice_data']
            
            messages.success(request, f'Invoice {invoice.invoice_number} created successfully!')
            return redirect('sales:invoice_detail', pk=invoice.pk)
        
        elif action == 'back':
            return redirect('sales:invoice_create_step2')
        
        return redirect('sales:invoice_create_step3')


class InvoiceListView(StaffRequiredMixin, ListView):
    model = Invoice
    template_name = 'sales/invoice_list_daisyui.html'  # Use DaisyUI template
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('items', 'items__product')
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        payment_filter = self.request.GET.get('payment_filter')
        
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(customer__company_name__icontains=search)
            )
        
        if status:
            queryset = queryset.filter(status=status)
        
        # Special filter for unpaid invoices
        if payment_filter == 'unpaid':
            queryset = queryset.exclude(status__in=['paid', 'cancelled', 'refunded'])
        elif payment_filter == 'overdue':
            queryset = queryset.filter(status='overdue')
        elif payment_filter == 'paid':
            queryset = queryset.filter(status='paid')
        
        return queryset.order_by('-invoice_date', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_payment_filter'] = self.request.GET.get('payment_filter', '')
        context['status_choices'] = Invoice.STATUS_CHOICES
        
        # Calculate statistics for current month only
        from django.db.models import Sum
        from django.utils import timezone
        from datetime import datetime
        
        # Get current month's date range
        now = timezone.now()
        current_month_start = datetime(now.year, now.month, 1)
        
        # Filter invoices for current month
        current_month_invoices = Invoice.objects.filter(
            invoice_date__year=now.year,
            invoice_date__month=now.month
        )
        
        total_invoices = current_month_invoices.count()
        total_revenue = current_month_invoices.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        paid_count = current_month_invoices.filter(status='paid').count()
        pending_count = current_month_invoices.filter(
            status__in=['draft', 'sent', 'viewed']
        ).count()
        
        context['total_invoices'] = total_invoices
        context['total_revenue'] = total_revenue
        context['paid_count'] = paid_count
        context['pending_count'] = pending_count
        
        return context


class InvoiceDetailView(StaffRequiredMixin, DetailView):
    model = Invoice
    template_name = 'sales/invoice_detail_daisyui.html'
    context_object_name = 'invoice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        context['payments'] = self.object.payments.all()
        return context


@staff_member_required
def invoice_update_tracking(request, pk):
    """Update tracking information for an invoice (AJAX)"""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        delivery_service = request.POST.get('delivery_service', '')
        post_tracking_number = request.POST.get('post_tracking_number', '')
        
        # Update the invoice
        invoice.delivery_service = delivery_service if delivery_service else None
        invoice.post_tracking_number = post_tracking_number
        invoice.save()
        
        # Get display value for delivery service
        delivery_service_display = invoice.get_delivery_service_display() if invoice.delivery_service else None
        
        return JsonResponse({
            'success': True,
            'delivery_service': invoice.delivery_service,
            'delivery_service_display': delivery_service_display,
            'post_tracking_number': invoice.post_tracking_number
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


class InvoiceCreateView(StaffRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'sales/invoice_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = InvoiceItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = InvoiceItemFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            form.instance.created_by = self.request.user
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            
            # Calculate totals
            self.calculate_invoice_totals()
            
            messages.success(self.request, 'Invoice created successfully!')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
    
    def calculate_invoice_totals(self):
        items = self.object.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (self.object.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (self.object.tax_rate / 100)
        total = subtotal_after_discount + tax_amount
        
        self.object.subtotal = subtotal
        self.object.discount_amount = discount_amount
        self.object.tax_amount = tax_amount
        self.object.total_amount = total
        self.object.balance_due = total - self.object.paid_amount
        self.object.save()
    
    def get_success_url(self):
        return reverse('sales:invoice_detail', kwargs={'pk': self.object.pk})


class InvoiceUpdateView(StaffRequiredMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'sales/invoice_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = InvoiceItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = InvoiceItemFormSet(instance=self.object)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            
            # Recalculate totals
            self.calculate_invoice_totals()
            
            messages.success(self.request, 'Invoice updated successfully!')
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
    
    def calculate_invoice_totals(self):
        items = self.object.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (self.object.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (self.object.tax_rate / 100)
        total = subtotal_after_discount + tax_amount
        
        self.object.subtotal = subtotal
        self.object.discount_amount = discount_amount
        self.object.tax_amount = tax_amount
        self.object.total_amount = total
        self.object.balance_due = total - self.object.paid_amount
        self.object.save()
    
    def get_success_url(self):
        return reverse('sales:invoice_detail', kwargs={'pk': self.object.pk})


class InvoiceDeleteView(StaffRequiredMixin, DeleteView):
    model = Invoice
    template_name = 'sales/invoice_confirm_delete.html'
    success_url = reverse_lazy('sales:invoice_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Invoice deleted successfully!')
        return super().delete(request, *args, **kwargs)


class InvoiceSendView(StaffRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        
        # TODO: Implement email sending logic here
        # For now, just update the status and sent date
        invoice.status = 'sent'
        invoice.sent_date = timezone.now()
        invoice.save()
        
        messages.success(request, f'Invoice {invoice.invoice_number} sent successfully!')
        return redirect('sales:invoice_detail', pk=pk)


# Invoice Item Views
class InvoiceItemCreateView(StaffRequiredMixin, CreateView):
    model = InvoiceItem
    fields = ['product', 'inventory', 'description', 'quantity', 'unit_price', 'discount_percent']
    template_name = 'sales/invoice_item_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = type('obj', (object,), {'invoice': get_object_or_404(Invoice, pk=self.kwargs['invoice_pk'])})
        return context
    
    def form_valid(self, form):
        invoice = get_object_or_404(Invoice, pk=self.kwargs['invoice_pk'])
        form.instance.invoice = invoice
        
        # Check if this is a serial managed product with inventory
        if form.instance.inventory:
            inventory = form.instance.inventory
            # Validate inventory is available
            if inventory.status != 'available':
                form.add_error('inventory', 'This inventory item is not available')
                return self.form_invalid(form)
            
            # Update inventory status
            inventory.status = 'sold'
            inventory.customer = invoice.customer
            inventory.sale_date = timezone.now().date()
            inventory.sale_price = form.instance.unit_price
            inventory.save()
            
            # Update description to include serial number
            form.instance.description = f"{inventory.product.name} (SN: {inventory.serial_number})"
        
        response = super().form_valid(form)
        
        # Recalculate invoice totals
        self.recalculate_invoice_totals(invoice)
        
        messages.success(self.request, 'Item added successfully!')
        return response
    
    def recalculate_invoice_totals(self, invoice):
        items = invoice.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (invoice.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (invoice.tax_rate / 100)
        total = subtotal_after_discount + tax_amount
        
        invoice.subtotal = subtotal
        invoice.discount_amount = discount_amount
        invoice.tax_amount = tax_amount
        invoice.total_amount = total
        invoice.balance_due = total - invoice.paid_amount
        invoice.save()
    
    def get_success_url(self):
        return reverse('sales:invoice_detail', kwargs={'pk': self.kwargs['invoice_pk']})


class InvoiceItemUpdateView(StaffRequiredMixin, UpdateView):
    model = InvoiceItem
    fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percent']
    template_name = 'sales/invoice_item_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Recalculate invoice totals
        self.recalculate_invoice_totals(self.object.invoice)
        
        messages.success(self.request, 'Item updated successfully!')
        return response
    
    def recalculate_invoice_totals(self, invoice):
        items = invoice.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (invoice.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (invoice.tax_rate / 100)
        total = subtotal_after_discount + tax_amount
        
        invoice.subtotal = subtotal
        invoice.discount_amount = discount_amount
        invoice.tax_amount = tax_amount
        invoice.total_amount = total
        invoice.balance_due = total - invoice.paid_amount
        invoice.save()
    
    def get_success_url(self):
        return reverse('sales:invoice_detail', kwargs={'pk': self.object.invoice.pk})


class InvoiceItemDeleteView(StaffRequiredMixin, DeleteView):
    model = InvoiceItem
    template_name = 'sales/invoice_item_confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        invoice = self.object.invoice
        response = super().delete(request, *args, **kwargs)
        
        # Recalculate invoice totals
        self.recalculate_invoice_totals(invoice)
        
        messages.success(request, 'Item removed successfully!')
        return response
    
    def recalculate_invoice_totals(self, invoice):
        items = invoice.items.all()
        subtotal = sum(item.line_total for item in items)
        
        discount_amount = subtotal * (invoice.discount_percent / 100)
        subtotal_after_discount = subtotal - discount_amount
        
        tax_amount = subtotal_after_discount * (invoice.tax_rate / 100)
        total = subtotal_after_discount + tax_amount
        
        invoice.subtotal = subtotal
        invoice.discount_amount = discount_amount
        invoice.tax_amount = tax_amount
        invoice.total_amount = total
        invoice.balance_due = total - invoice.paid_amount
        invoice.save()
    
    def get_success_url(self):
        return reverse('sales:invoice_detail', kwargs={'pk': self.kwargs['invoice_pk']})


# Payment Views
class PaymentCreateView(StaffRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'sales/payment_form_daisyui.html'
    
    def get_initial(self):
        initial = super().get_initial()
        if 'invoice_pk' in self.kwargs:
            invoice = get_object_or_404(Invoice, pk=self.kwargs['invoice_pk'])
            initial['invoice'] = invoice
            # Set customer from invoice (even if None for shop orders)
            initial['customer'] = invoice.customer
            initial['amount'] = invoice.balance_due
        return initial
    
    def form_valid(self, form):
        form.instance.processed_by = self.request.user
        response = super().form_valid(form)
        
        # Update invoice payment status
        if form.instance.invoice:
            invoice = form.instance.invoice
            invoice.paid_amount += form.instance.amount
            invoice.update_status()
            invoice.save()
        
        # Update order payment status if linked
        if form.instance.order:
            order = form.instance.order
            order.paid_amount += form.instance.amount
            order.update_payment_status()
            order.save()
        
        messages.success(self.request, 'Payment recorded successfully!')
        return response
    
    def get_success_url(self):
        if self.object.invoice:
            return reverse('sales:invoice_detail', kwargs={'pk': self.object.invoice.pk})
        elif self.object.order:
            return reverse('sales:order_detail', kwargs={'pk': self.object.order.pk})
        else:
            return reverse('sales:payment_detail', kwargs={'pk': self.object.pk})


class PaymentDetailView(StaffRequiredMixin, DetailView):
    model = Payment
    template_name = 'sales/payment_detail.html'
    context_object_name = 'payment'


# API Views
class AvailableInventoryAPIView(StaffRequiredMixin, View):
    """API endpoint to get available inventory items for a product"""
    
    def get(self, request, product_id):
        try:
            product = get_object_or_404(Product, pk=product_id)
            
            # Get available inventory items for this product
            inventory_items = Inventory.objects.filter(
                product=product,
                status='available'
            ).select_related('product')
            
            items_data = []
            for item in inventory_items:
                items_data.append({
                    'id': item.id,
                    'serial_number': item.serial_number,
                    'condition': item.condition,
                    'product_name': item.product.name,
                    'location': item.current_location or 'N/A'
                })
            
            return JsonResponse({
                'success': True,
                'items': items_data,
                'count': len(items_data)
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


class InvoicePDFView(StaffRequiredMixin, View):
    """Generate PDF for an invoice"""
    
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        
        # Create a file-like buffer to receive PDF data
        buffer = BytesIO()
        
        # Create the PDF object, using the buffer as its "file"
        template = get_template('sales/invoice_pdf.html')
        context = {
            'invoice': invoice,
            'items': invoice.items.all(),
            'company_name': 'DCDG Dental',
            'company_address': '123 Business St, City, State 12345',
            'company_phone': '(555) 123-4567',
            'company_email': 'info@dcdgdental.com',
        }
        html = template.render(context)
        
        # Create PDF
        pisa_status = pisa.CreatePDF(html, dest=buffer)
        
        # If error, show error message
        if pisa_status.err:
            return HttpResponse('Error generating PDF', status=400)
        
        # File response
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
        
        return response