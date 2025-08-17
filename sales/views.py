from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    View,
)
from django.contrib import messages
from django.db.models import Sum, Q, F
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import json

from .models import (
    Quote,
    QuoteItem,
    Order,
    OrderItem,
    Invoice,
    InvoiceItem,
    Payment,
    InvoiceShipment,
    ShipmentItem,
)
from .forms import (
    QuoteForm,
    QuoteItemForm,
    OrderForm,
    OrderItemForm,
    InvoiceForm,
    InvoiceItemFormSet,
    PaymentForm,
    InvoiceShipmentForm,
    ShipmentItemFormSet,
)
from customer.models import Customer, CustomerAddress
from product.models import Product, Inventory
from purchases.models import Supplier


class InvoiceApproveView(UpdateView):
    model = Invoice
    fields = [
        "invoice_date",
        "customer",
        "subtotal",
        "tax_amount",
        "total_amount",
        "accounting_status",
    ]
    success_url = reverse_lazy("sales:list")

    def form_valid(self, form):
        resp = super().form_valid(form)
        invoice = self.object
        if (
            invoice.accounting_status == Invoice.ACCOUNTING_STATUS_CHOICES.APPROVED
            and not invoice.is_posted
        ):
            invoice.approve()  # 승인 & 전기
            messages.success(self.request, f"매출 #{invoice.pk} 승인/전기 완료")
        return resp


# Mixin to require staff membership
class StaffRequiredMixin(LoginRequiredMixin):
    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


# Quote Views
class QuoteListView(StaffRequiredMixin, ListView):
    model = Quote
    template_name = "sales/quote_list.html"
    context_object_name = "quotes"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("customer")

        # Search functionality
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(quote_number__icontains=search)
                | Q(customer__first_name__icontains=search)
                | Q(customer__last_name__icontains=search)
                | Q(customer__company_name__icontains=search)
            )

        # Status filter
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by("-created_at")


class QuoteDetailView(StaffRequiredMixin, DetailView):
    model = Quote
    template_name = "sales/quote_detail.html"
    context_object_name = "quote"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items.select_related("product")
        return context


class QuoteCreateView(StaffRequiredMixin, CreateView):
    model = Quote
    form_class = QuoteForm
    template_name = "sales/quote_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Quote created successfully!")
        return response

    def get_success_url(self):
        return reverse("sales:quote_detail", kwargs={"pk": self.object.pk})


class QuoteUpdateView(StaffRequiredMixin, UpdateView):
    model = Quote
    form_class = QuoteForm
    template_name = "sales/quote_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Quote updated successfully!")
        return response

    def get_success_url(self):
        return reverse("sales:quote_detail", kwargs={"pk": self.object.pk})


class QuoteDeleteView(StaffRequiredMixin, DeleteView):
    model = Quote
    template_name = "sales/quote_confirm_delete.html"
    success_url = reverse_lazy("sales:quote_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Quote deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Quote Item Views
class QuoteItemCreateView(StaffRequiredMixin, CreateView):
    model = QuoteItem
    form_class = QuoteItemForm
    template_name = "sales/quote_item_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["quote"] = get_object_or_404(Quote, pk=self.kwargs["quote_pk"])
        return context

    def form_valid(self, form):
        quote = get_object_or_404(Quote, pk=self.kwargs["quote_pk"])
        form.instance.quote = quote
        response = super().form_valid(form)
        messages.success(self.request, "Item added to quote!")
        return response

    def get_success_url(self):
        return reverse("sales:quote_detail", kwargs={"pk": self.kwargs["quote_pk"]})


class QuoteItemUpdateView(StaffRequiredMixin, UpdateView):
    model = QuoteItem
    form_class = QuoteItemForm
    template_name = "sales/quote_item_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["quote"] = self.object.quote
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Quote item updated!")
        return response

    def get_success_url(self):
        return reverse("sales:quote_detail", kwargs={"pk": self.object.quote.pk})


class QuoteItemDeleteView(StaffRequiredMixin, DeleteView):
    model = QuoteItem
    template_name = "sales/quote_item_confirm_delete.html"

    def get_success_url(self):
        messages.success(self.request, "Item removed from quote!")
        return reverse("sales:quote_detail", kwargs={"pk": self.object.quote.pk})


# Order Views
class OrderListView(StaffRequiredMixin, ListView):
    model = Order
    template_name = "sales/order_list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("customer")

        # Search functionality
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search)
                | Q(customer__first_name__icontains=search)
                | Q(customer__last_name__icontains=search)
                | Q(customer__company_name__icontains=search)
            )

        # Status filter
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by("-created_at")


class OrderDetailView(StaffRequiredMixin, DetailView):
    model = Order
    template_name = "sales/order_detail.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items.select_related("product")
        return context


class OrderCreateView(StaffRequiredMixin, CreateView):
    model = Order
    form_class = OrderForm
    template_name = "sales/order_form.html"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Order created successfully!")
        return response

    def get_success_url(self):
        return reverse("sales:order_detail", kwargs={"pk": self.object.pk})


class OrderUpdateView(StaffRequiredMixin, UpdateView):
    model = Order
    form_class = OrderForm
    template_name = "sales/order_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Order updated successfully!")
        return response

    def get_success_url(self):
        return reverse("sales:order_detail", kwargs={"pk": self.object.pk})


class OrderDeleteView(StaffRequiredMixin, DeleteView):
    model = Order
    template_name = "sales/order_confirm_delete.html"
    success_url = reverse_lazy("sales:order_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Order deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Order Item Views
class OrderItemCreateView(StaffRequiredMixin, CreateView):
    model = OrderItem
    fields = ["product", "quantity", "unit_price", "discount_percent", "notes"]
    template_name = "sales/order_item_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order"] = get_object_or_404(Order, pk=self.kwargs["order_pk"])
        return context

    def form_valid(self, form):
        order = get_object_or_404(Order, pk=self.kwargs["order_pk"])
        form.instance.order = order
        response = super().form_valid(form)
        messages.success(self.request, "Item added to order!")
        return response

    def get_success_url(self):
        return reverse("sales:order_detail", kwargs={"pk": self.kwargs["order_pk"]})


class OrderItemUpdateView(StaffRequiredMixin, UpdateView):
    model = OrderItem
    fields = ["product", "quantity", "unit_price", "discount_percent", "notes"]
    template_name = "sales/order_item_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order"] = self.object.order
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Order item updated!")
        return response

    def get_success_url(self):
        return reverse("sales:order_detail", kwargs={"pk": self.object.order.pk})


class OrderItemDeleteView(StaffRequiredMixin, DeleteView):
    model = OrderItem
    template_name = "sales/order_item_confirm_delete.html"

    def get_success_url(self):
        messages.success(self.request, "Item removed from order!")
        return reverse("sales:order_detail", kwargs={"pk": self.object.order.pk})


# Invoice Views
class InvoiceListView(StaffRequiredMixin, ListView):
    model = Invoice
    template_name = "sales/invoice_list_daisyui.html"
    context_object_name = "invoices"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("customer")

        # Search functionality
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search)
                | Q(customer__first_name__icontains=search)
                | Q(customer__last_name__icontains=search)
                | Q(customer__company_name__icontains=search)
            )

        # Status filter
        status = self.request.GET.get("status")
        if status:
            if status == "overdue":
                # Special handling for overdue - check if due_date has passed and not paid
                from django.utils import timezone

                today = timezone.now().date()
                queryset = queryset.filter(
                    due_date__lt=today, status__in=["sent", "partial"]
                )
            else:
                queryset = queryset.filter(status=status)

        # Date range filter
        date_from = self.request.GET.get("date_from")
        if date_from:
            queryset = queryset.filter(invoice_date__gte=date_from)

        date_to = self.request.GET.get("date_to")
        if date_to:
            queryset = queryset.filter(invoice_date__lte=date_to)

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate stats for current month
        from django.utils import timezone
        from django.db.models import Sum, Count
        from datetime import datetime

        # Get current month's start and end dates
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Get all invoices for current month (not filtered)
        month_invoices = Invoice.objects.filter(
            invoice_date__gte=month_start, invoice_date__lte=today
        )

        # Calculate statistics
        context["total_invoices"] = month_invoices.count()

        # Total revenue (sum of total_amount for all invoices this month)
        context["total_revenue"] = (
            month_invoices.aggregate(total=Sum("total_amount"))["total"] or 0
        )

        # Paid count (invoices with status 'paid' this month)
        context["paid_count"] = month_invoices.filter(status="paid").count()

        # Pending count (invoices with status in 'sent', 'partial', 'overdue' this month)
        context["pending_count"] = month_invoices.filter(
            status__in=["sent", "partial", "overdue", "draft"]
        ).count()

        # Add filter values to context for form persistence
        context["search_query"] = self.request.GET.get("search", "")
        context["status_filter"] = self.request.GET.get("status", "")
        context["date_from"] = self.request.GET.get("date_from", "")
        context["date_to"] = self.request.GET.get("date_to", "")

        return context


class InvoiceDetailView(StaffRequiredMixin, DetailView):
    model = Invoice
    template_name = "sales/invoice_detail_daisyui.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items.select_related("product")
        context["payments"] = self.object.payments.all().order_by("-payment_date")
        context["shipments"] = self.object.shipments.all().order_by("-created_at")
        return context


# Invoice Create 3-Step Process
class InvoiceCreateStep1View(StaffRequiredMixin, TemplateView):
    template_name = "sales/invoice_create_step1_daisyui.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get customers with their default addresses
        customers = Customer.objects.prefetch_related("addresses").order_by(
            "company_name", "last_name", "first_name"
        )

        # Add default address to each customer
        for customer in customers:
            customer.default_address = customer.get_default_address

        context["customers"] = customers
        return context

    def post(self, request):
        customer_id = request.POST.get("customer_id")
        if not customer_id:
            messages.error(request, "Please select a customer")
            return redirect("sales:invoice_create_step1")

        # Store in session
        request.session["invoice_customer_id"] = customer_id
        return redirect("sales:invoice_create_step2")


class InvoiceCreateStep2View(StaffRequiredMixin, TemplateView):
    template_name = "sales/invoice_create_step2_daisyui.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if customer is selected
        if "invoice_customer_id" not in request.session:
            messages.warning(request, "Please select a customer first")
            return redirect("sales:invoice_create_step1")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer_id = self.request.session.get("invoice_customer_id")
        context["customer"] = get_object_or_404(Customer, pk=customer_id)
        context["products"] = Product.objects.filter(status="active").order_by("name")

        # Get saved items from session
        invoice_items = self.request.session.get("invoice_items", [])
        context["invoice_items"] = invoice_items

        # Calculate subtotal
        subtotal = 0
        for item in invoice_items:
            try:
                subtotal += float(item.get("line_total", 0))
            except (ValueError, TypeError):
                pass
        context["subtotal"] = subtotal

        return context

    def post(self, request):
        action = request.POST.get("action")

        # Get existing items from session
        items = request.session.get("invoice_items", [])

        if action == "add_item":
            # Add a single item
            product_id = request.POST.get("product_id")
            description = request.POST.get("description")
            quantity = request.POST.get("quantity")
            unit_price = request.POST.get("unit_price")
            discount_percent = request.POST.get("discount_percent", "0")
            inventory_id = request.POST.get("inventory_id")

            if description and quantity and unit_price:
                # Calculate line total
                qty = float(quantity)
                price = float(unit_price)
                discount = float(discount_percent)
                line_total = qty * price * (1 - discount / 100)

                new_item = {
                    "product_id": product_id,
                    "description": description,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_percent": discount_percent,
                    "inventory_id": inventory_id,
                    "line_total": str(line_total),
                }

                # Get product name if product was selected
                if product_id:
                    try:
                        product = Product.objects.get(pk=product_id)
                        new_item["product_name"] = product.name
                    except Product.DoesNotExist:
                        pass

                items.append(new_item)
                request.session["invoice_items"] = items
                messages.success(request, "Item added successfully")
            else:
                messages.error(request, "Please fill in all required fields")

            return redirect("sales:invoice_create_step2")

        elif action == "remove_item":
            # Remove an item
            item_index = request.POST.get("item_index")
            if item_index is not None:
                try:
                    index = int(item_index)
                    if 0 <= index < len(items):
                        items.pop(index)
                        request.session["invoice_items"] = items
                        messages.success(request, "Item removed")
                except (ValueError, IndexError):
                    messages.error(request, "Invalid item index")

            return redirect("sales:invoice_create_step2")

        elif action == "next":
            # Proceed to next step
            if not items:
                messages.error(request, "Please add at least one item")
                return redirect("sales:invoice_create_step2")

            return redirect("sales:invoice_create_step3")

        # Default: go back to step 2
        return redirect("sales:invoice_create_step2")


class InvoiceCreateStep3View(StaffRequiredMixin, TemplateView):
    template_name = "sales/invoice_create_step3_daisyui.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if previous steps are completed
        if (
            "invoice_customer_id" not in request.session
            or "invoice_items" not in request.session
        ):
            messages.warning(request, "Please complete previous steps")
            return redirect("sales:invoice_create_step1")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer_id = self.request.session.get("invoice_customer_id")
        context["customer"] = get_object_or_404(Customer, pk=customer_id)

        # Process items
        items = self.request.session.get("invoice_items", [])
        processed_items = []
        subtotal = Decimal("0")

        for item in items:
            # Get product if ID exists
            product = None
            if item.get("product_id"):
                try:
                    product = Product.objects.get(pk=item["product_id"])
                except Product.DoesNotExist:
                    pass

            quantity = Decimal(item.get("quantity", "0"))
            unit_price = Decimal(item.get("unit_price", "0"))
            discount_percent = Decimal(item.get("discount_percent", "0"))

            line_total = quantity * unit_price
            discount_amount = line_total * (discount_percent / 100)
            total = line_total - discount_amount

            processed_items.append(
                {
                    "product": product,
                    "product_name": item.get("product_name", ""),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_percent": discount_percent,
                    "description": item.get("description", ""),
                    "line_total": total,  # Use total after discount
                    "discount_amount": discount_amount,
                    "total": total,
                }
            )
            subtotal += total

        context["invoice_items"] = (
            processed_items  # Changed from 'items' to 'invoice_items'
        )
        context["subtotal"] = subtotal

        # Get tax rate and shipping cost from session or defaults
        context["tax_rate"] = self.request.session.get("invoice_tax_rate", Decimal("0"))
        context["shipping_cost"] = self.request.session.get(
            "invoice_shipping_cost", Decimal("0")
        )

        # Calculate tax amount and total
        tax_amount = subtotal * (context["tax_rate"] / Decimal("100"))
        context["tax_amount"] = tax_amount
        context["total_amount"] = subtotal + tax_amount + context["shipping_cost"]

        # Get or generate invoice number
        from datetime import datetime

        context["invoice_number"] = (
            f"INV-{datetime.now().strftime('%Y%m%d')}-{Invoice.objects.count() + 1:04d}"
        )
        context["invoice_date"] = datetime.now().date()
        context["due_date"] = datetime.now().date() + timedelta(days=30)

        # Get user's organization
        from customer.models import Organization

        if hasattr(self.request.user, "organization"):
            context["organization"] = self.request.user.organization
        else:
            # Try to get the first active organization (default organization)
            context["organization"] = Organization.objects.filter(
                is_active=True
            ).first()

        return context

    def post(self, request):
        action = request.POST.get("action")

        # Get data from session
        customer_id = request.session.get("invoice_customer_id")
        items_data = request.session.get("invoice_items", [])

        # Get form data
        invoice_number = request.POST.get("invoice_number")
        invoice_date = request.POST.get("invoice_date")
        due_date = request.POST.get("due_date")
        tax_rate = request.POST.get("tax_rate", "0")
        shipping_cost = request.POST.get("shipping_cost", "0")
        discount_percent = request.POST.get("discount_percent", "0")
        notes = request.POST.get("notes", "")
        internal_notes = request.POST.get("internal_notes", "")

        # Handle update action - save to session and refresh
        if action == "update":
            request.session["invoice_tax_rate"] = (
                Decimal(tax_rate) if tax_rate else Decimal("0")
            )
            request.session["invoice_shipping_cost"] = (
                Decimal(shipping_cost) if shipping_cost else Decimal("0")
            )
            return redirect("sales:invoice_create_step3")

        # Handle back action
        if action == "back":
            return redirect("sales:invoice_create_step2")

        # Get shipping address
        shipping_address_id = request.POST.get("shipping_address")
        customer = get_object_or_404(Customer, pk=customer_id)

        # Create invoice (for save action)
        with transaction.atomic():
            invoice = Invoice.objects.create(
                customer=customer,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                due_date=due_date,
                status="draft",
                tax_rate=Decimal(tax_rate) if tax_rate else Decimal("0"),
                shipping_cost=Decimal(shipping_cost) if shipping_cost else Decimal("0"),
                discount_percent=(
                    Decimal(discount_percent) if discount_percent else Decimal("0")
                ),
                notes=notes,
                internal_notes=internal_notes,
                # Add customer info for compatibility with shop orders
                first_name=customer.first_name,
                last_name=customer.last_name,
                email=customer.email,
                phone=customer.phone if customer.phone else "",
            )

            # Set billing address
            default_address = customer.get_default_address
            if default_address:
                invoice.billing_address_line1 = default_address.address_line1
                invoice.billing_address_line2 = default_address.address_line2 or ""
                invoice.billing_city = default_address.city
                invoice.billing_state = default_address.state
                invoice.billing_postal_code = default_address.postal_code
                invoice.billing_country = default_address.country

            # Set shipping address if provided
            if shipping_address_id:
                try:
                    shipping_addr = CustomerAddress.objects.get(
                        pk=shipping_address_id, customer=customer
                    )
                    invoice.shipping_address_line1 = shipping_addr.address_line1
                    invoice.shipping_address_line2 = shipping_addr.address_line2 or ""
                    invoice.shipping_city = shipping_addr.city
                    invoice.shipping_state = shipping_addr.state
                    invoice.shipping_postal_code = shipping_addr.postal_code
                    invoice.shipping_country = shipping_addr.country
                except CustomerAddress.DoesNotExist:
                    pass

            invoice.save()

            # Create invoice items
            for item_data in items_data:
                # Get product if ID exists
                product = None
                if item_data.get("product_id"):
                    try:
                        product = Product.objects.get(pk=item_data["product_id"])
                    except Product.DoesNotExist:
                        pass

                # Get description
                description = item_data.get("description", "")
                if not description and product:
                    description = product.name

                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=product,
                    description=description,
                    quantity=Decimal(item_data.get("quantity", "0")),
                    unit_price=Decimal(item_data.get("unit_price", "0")),
                    discount_percent=Decimal(item_data.get("discount_percent", "0")),
                )

            # Calculate invoice totals after all items are created
            invoice.calculate_totals()

        # Clear session
        if "invoice_customer_id" in request.session:
            del request.session["invoice_customer_id"]
        if "invoice_items" in request.session:
            del request.session["invoice_items"]
        if "invoice_tax_rate" in request.session:
            del request.session["invoice_tax_rate"]
        if "invoice_shipping_cost" in request.session:
            del request.session["invoice_shipping_cost"]

        messages.success(request, f"Invoice {invoice_number} created successfully!")
        return redirect("sales:invoice_detail", pk=invoice.pk)


class InvoiceUpdateView(StaffRequiredMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "sales/invoice_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = InvoiceItemFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["formset"] = InvoiceItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Invoice updated successfully!")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("sales:invoice_detail", kwargs={"pk": self.object.pk})


# Invoice Edit 3-Step Process
class InvoiceEditStep1View(StaffRequiredMixin, TemplateView):
    template_name = "sales/invoice_edit_step1_daisyui.html"

    def dispatch(self, request, *args, **kwargs):
        self.invoice = get_object_or_404(Invoice, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.invoice
        # Get customers with their default addresses
        customers = Customer.objects.prefetch_related("addresses").order_by(
            "company_name", "last_name", "first_name"
        )

        # Add default address to each customer
        for customer in customers:
            customer.default_address = customer.get_default_address

        context["customers"] = customers
        context["current_customer_id"] = (
            self.invoice.customer.pk if self.invoice.customer else None
        )
        return context

    def post(self, request, pk):
        customer_id = request.POST.get("customer_id")
        if not customer_id:
            messages.error(request, "Please select a customer")
            return redirect("sales:invoice_edit_step1", pk=pk)

        # Store in session
        request.session["edit_invoice_customer_id"] = customer_id
        request.session["edit_invoice_pk"] = pk
        return redirect("sales:invoice_edit_step2", pk=pk)


class InvoiceEditStep2View(StaffRequiredMixin, TemplateView):
    template_name = "sales/invoice_edit_step2_daisyui.html"

    def dispatch(self, request, *args, **kwargs):
        self.invoice = get_object_or_404(Invoice, pk=kwargs["pk"])
        # Check if customer is selected
        if "edit_invoice_customer_id" not in request.session:
            # Use existing customer if not in session
            request.session["edit_invoice_customer_id"] = (
                self.invoice.customer.pk if self.invoice.customer else None
            )
        if not request.session.get("edit_invoice_customer_id"):
            messages.warning(request, "Please select a customer first")
            return redirect("sales:invoice_edit_step1", pk=self.invoice.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.invoice
        customer_id = self.request.session.get("edit_invoice_customer_id")
        context["customer"] = get_object_or_404(Customer, pk=customer_id)
        context["products"] = Product.objects.filter(status="active").order_by("name")

        # Get existing invoice items
        invoice_items = []
        for item in self.invoice.items.all():
            invoice_items.append(
                {
                    "id": item.id,
                    "product_id": str(item.product.pk) if item.product else "",
                    "product_name": item.product.name if item.product else "",
                    "description": item.description,
                    "quantity": str(item.quantity),
                    "unit_price": str(item.unit_price),
                    "discount_percent": str(item.discount_percent),
                    "line_total": str(item.line_total),
                    "inventory_id": str(item.inventory.pk) if item.inventory else "",
                }
            )

        # Override with session items if available (user might have made changes)
        if "edit_invoice_items" in self.request.session:
            context["invoice_items"] = self.request.session["edit_invoice_items"]
        else:
            context["invoice_items"] = invoice_items
            # Store in session for consistency
            self.request.session["edit_invoice_items"] = invoice_items

        # Calculate subtotal
        subtotal = 0
        for item in context["invoice_items"]:
            try:
                subtotal += float(item.get("line_total", 0))
            except (ValueError, TypeError):
                pass
        context["subtotal"] = subtotal

        return context

    def post(self, request, pk):
        action = request.POST.get("action")

        # Get existing items from session
        items = request.session.get("edit_invoice_items", [])

        if action == "add_item":
            # Add a single item
            product_id = request.POST.get("product_id")
            description = request.POST.get("description")
            quantity = request.POST.get("quantity")
            unit_price = request.POST.get("unit_price")
            discount_percent = request.POST.get("discount_percent", "0")
            inventory_id = request.POST.get("inventory_id")

            if description and quantity and unit_price:
                # Calculate line total
                qty = float(quantity)
                price = float(unit_price)
                discount = float(discount_percent)
                line_total = qty * price * (1 - discount / 100)

                new_item = {
                    "id": None,  # New item
                    "product_id": product_id,
                    "description": description,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_percent": discount_percent,
                    "inventory_id": inventory_id,
                    "line_total": str(line_total),
                }

                # Get product name if product was selected
                if product_id:
                    try:
                        product = Product.objects.get(pk=product_id)
                        new_item["product_name"] = product.name
                    except Product.DoesNotExist:
                        pass

                items.append(new_item)
                request.session["edit_invoice_items"] = items
                messages.success(request, "Item added successfully")
            else:
                messages.error(request, "Please fill in all required fields")

            return redirect("sales:invoice_edit_step2", pk=pk)

        elif action == "remove_item":
            # Remove an item
            item_index = request.POST.get("item_index")
            if item_index is not None:
                try:
                    index = int(item_index)
                    if 0 <= index < len(items):
                        removed_item = items.pop(index)
                        # Store removed item IDs for deletion later
                        if removed_item.get("id"):
                            removed_ids = request.session.get(
                                "edit_invoice_removed_items", []
                            )
                            removed_ids.append(removed_item["id"])
                            request.session["edit_invoice_removed_items"] = removed_ids
                        request.session["edit_invoice_items"] = items
                        messages.success(request, "Item removed")
                except (ValueError, IndexError):
                    messages.error(request, "Invalid item index")

            return redirect("sales:invoice_edit_step2", pk=pk)

        elif action == "next":
            # Proceed to next step
            if not items:
                messages.error(request, "Please add at least one item")
                return redirect("sales:invoice_edit_step2", pk=pk)

            return redirect("sales:invoice_edit_step3", pk=pk)

        # Default: go back to step 2
        return redirect("sales:invoice_edit_step2", pk=pk)


class InvoiceEditStep3View(StaffRequiredMixin, TemplateView):
    template_name = "sales/invoice_edit_step3_daisyui.html"

    def dispatch(self, request, *args, **kwargs):
        self.invoice = get_object_or_404(Invoice, pk=kwargs["pk"])
        # Check if previous steps are completed
        if (
            "edit_invoice_customer_id" not in request.session
            or "edit_invoice_items" not in request.session
        ):
            messages.warning(request, "Please complete previous steps")
            return redirect("sales:invoice_edit_step1", pk=self.invoice.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.invoice
        customer_id = self.request.session.get("edit_invoice_customer_id")
        context["customer"] = get_object_or_404(Customer, pk=customer_id)

        # Process items
        items = self.request.session.get("edit_invoice_items", [])
        processed_items = []
        subtotal = Decimal("0")

        for item in items:
            # Get product if ID exists
            product = None
            if item.get("product_id"):
                try:
                    product = Product.objects.get(pk=item["product_id"])
                except Product.DoesNotExist:
                    pass

            quantity = Decimal(item.get("quantity", "0"))
            unit_price = Decimal(item.get("unit_price", "0"))
            discount_percent = Decimal(item.get("discount_percent", "0"))

            line_total = quantity * unit_price
            discount_amount = line_total * (discount_percent / 100)
            total = line_total - discount_amount

            processed_items.append(
                {
                    "id": item.get("id"),
                    "product": product,
                    "product_name": item.get("product_name", ""),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_percent": discount_percent,
                    "description": item.get("description", ""),
                    "line_total": total,
                    "discount_amount": discount_amount,
                    "total": total,
                }
            )
            subtotal += total

        context["invoice_items"] = processed_items
        context["subtotal"] = subtotal

        # Use existing invoice details
        context["invoice_number"] = self.invoice.invoice_number
        context["invoice_date"] = self.invoice.invoice_date
        context["due_date"] = self.invoice.due_date
        context["tax_rate"] = self.invoice.tax_rate
        context["shipping_cost"] = self.invoice.shipping_cost
        context["discount_percent"] = self.invoice.discount_percent
        context["status"] = self.invoice.status
        context["notes"] = self.invoice.notes
        context["internal_notes"] = self.invoice.internal_notes

        # Calculate amounts for display
        discount_amount = subtotal * (self.invoice.discount_percent / Decimal("100"))
        discounted_subtotal = subtotal - discount_amount
        tax_amount = discounted_subtotal * (self.invoice.tax_rate / Decimal("100"))
        tax_amount = (
            discounted_subtotal * (self.invoice.tax_rate / Decimal("100"))
        ).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP  # 소수점 2자리
        )
        total = discounted_subtotal + tax_amount + self.invoice.shipping_cost

        context["discount_amount"] = discount_amount
        context["tax_amount"] = tax_amount
        context["total"] = total

        # Get user's organization
        from customer.models import Organization

        if hasattr(self.request.user, "organization"):
            context["organization"] = self.request.user.organization
        else:
            context["organization"] = Organization.objects.filter(
                is_active=True
            ).first()

        return context

    def post(self, request, pk):
        # Get data from session
        customer_id = request.session.get("edit_invoice_customer_id")
        items_data = request.session.get("edit_invoice_items", [])
        removed_items = request.session.get("edit_invoice_removed_items", [])

        # Get form data
        invoice_number = request.POST.get("invoice_number")
        invoice_date = request.POST.get("invoice_date")
        due_date = request.POST.get("due_date")
        tax_rate = request.POST.get("tax_rate", "0")
        shipping_cost = request.POST.get("shipping_cost", "0")
        discount_percent = request.POST.get("discount_percent", "0")
        status = request.POST.get("status", "sent")
        notes = request.POST.get("notes", "")
        internal_notes = request.POST.get("internal_notes", "")

        customer = get_object_or_404(Customer, pk=customer_id)
        invoice = get_object_or_404(Invoice, pk=pk)

        # Update invoice
        with transaction.atomic():
            invoice.customer = customer
            invoice.invoice_number = invoice_number
            invoice.invoice_date = invoice_date
            invoice.due_date = due_date
            invoice.tax_rate = Decimal(tax_rate) if tax_rate else Decimal("0")
            invoice.shipping_cost = (
                Decimal(shipping_cost) if shipping_cost else Decimal("0")
            )
            invoice.discount_percent = (
                Decimal(discount_percent) if discount_percent else Decimal("0")
            )
            invoice.status = status
            invoice.notes = notes
            invoice.internal_notes = internal_notes

            # Update customer info
            invoice.first_name = customer.first_name
            invoice.last_name = customer.last_name
            invoice.email = customer.email
            invoice.phone = customer.phone if customer.phone else ""

            # Update billing address
            default_address = customer.get_default_address
            if default_address:
                invoice.billing_address_line1 = default_address.address_line1
                invoice.billing_address_line2 = default_address.address_line2 or ""
                invoice.billing_city = default_address.city
                invoice.billing_state = default_address.state
                invoice.billing_postal_code = default_address.postal_code
                invoice.billing_country = default_address.country

            invoice.save()

            # Delete removed items
            if removed_items:
                InvoiceItem.objects.filter(
                    id__in=removed_items, invoice=invoice
                ).delete()

            # Update or create invoice items
            for item_data in items_data:
                item_id = item_data.get("id")

                # Get product if ID exists
                product = None
                if item_data.get("product_id"):
                    try:
                        product = Product.objects.get(pk=item_data["product_id"])
                    except Product.DoesNotExist:
                        pass

                # Get description
                description = item_data.get("description", "")
                if not description and product:
                    description = product.name

                item_values = {
                    "product": product,
                    "description": description,
                    "quantity": Decimal(item_data.get("quantity", "0")),
                    "unit_price": Decimal(item_data.get("unit_price", "0")),
                    "discount_percent": Decimal(item_data.get("discount_percent", "0")),
                }

                if item_id:
                    # Update existing item
                    try:
                        item = InvoiceItem.objects.get(id=item_id, invoice=invoice)
                        for key, value in item_values.items():
                            setattr(item, key, value)
                        item.save()
                    except InvoiceItem.DoesNotExist:
                        # Item was deleted, create new one
                        InvoiceItem.objects.create(invoice=invoice, **item_values)
                else:
                    # Create new item
                    InvoiceItem.objects.create(invoice=invoice, **item_values)

            # Calculate invoice totals after all items are updated
            invoice.calculate_totals()

        # Clear session
        session_keys = [
            "edit_invoice_customer_id",
            "edit_invoice_items",
            "edit_invoice_removed_items",
            "edit_invoice_pk",
        ]
        for key in session_keys:
            if key in request.session:
                del request.session[key]

        messages.success(request, f"Invoice {invoice_number} updated successfully!")
        return redirect("sales:invoice_detail", pk=invoice.pk)


class InvoiceDeleteView(StaffRequiredMixin, DeleteView):
    model = Invoice
    template_name = "sales/invoice_confirm_delete.html"
    success_url = reverse_lazy("sales:invoice_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Invoice deleted successfully!")
        return super().delete(request, *args, **kwargs)


@login_required
@require_POST
def invoice_recalculate(request, pk):
    """Recalculate invoice totals, payment totals, and update status."""
    invoice = get_object_or_404(Invoice, pk=pk)

    # Recalculate invoice totals
    invoice.calculate_totals()

    # Calculate payment total
    from decimal import Decimal
    from django.db import models

    total_payments = invoice.payments.filter(status="completed").aggregate(
        total=models.Sum("amount")
    )["total"] or Decimal("0")

    # Round to 2 decimal places
    from decimal import ROUND_HALF_UP

    invoice.paid_amount = total_payments.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Update payment status based on payments
    if total_payments == 0:
        invoice.payment_status = "unpaid"
        if invoice.status in ["draft", "unsent"]:
            invoice.status = "sent"  # Set to sent if not paid yet
    elif total_payments < invoice.total_amount:
        # invoice.payment_status = 'partial'
        invoice.status = "partial"
    elif total_payments >= invoice.total_amount:
        # invoice.payment_status = 'paid'
        invoice.status = "paid"
        if total_payments > invoice.total_amount:
            invoice.status = "overpaid"
    print(
        "invoice.status:",
        invoice.status,
        "invoice.paid_amount:",
        invoice.paid_amount,
        "invoice.total_amount:",
        invoice.total_amount,
    )
    # Recalculate balance due with rounding
    invoice.balance_due = (invoice.total_amount - invoice.paid_amount).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    invoice.save()

    messages.success(
        request,
        f"Invoice {invoice.invoice_number} recalculated. "
        f"Total: ${invoice.total_amount}, Paid: ${invoice.paid_amount}, "
        f"Balance: ${invoice.balance_due}, Status: {invoice.get_status_display()}",
    )
    return redirect("sales:invoice_detail", pk=pk)


class InvoiceSendView(StaffRequiredMixin, DetailView):
    model = Invoice
    template_name = "sales/invoice_send.html"

    def post(self, request, *args, **kwargs):
        invoice = self.get_object()
        # TODO: Implement email sending logic
        messages.success(
            request, f"Invoice {invoice.invoice_number} sent successfully!"
        )
        return redirect("sales:invoice_detail", pk=invoice.pk)


# Invoice tracking update
@staff_member_required
def invoice_update_tracking(request, pk):
    if request.method == "POST":
        invoice = get_object_or_404(Invoice, pk=pk)
        tracking_number = request.POST.get("tracking_number", "")
        carrier = request.POST.get("carrier", "")

        # Update invoice tracking info
        # Note: You may want to add these fields to the Invoice model
        # invoice.tracking_number = tracking_number
        # invoice.carrier = carrier
        # invoice.save()

        messages.success(request, "Tracking information updated!")
        return redirect("sales:invoice_detail", pk=pk)

    return redirect("sales:invoice_detail", pk=pk)


@login_required
@require_POST
def invoice_mark_paid(request, pk):
    """Quick action to mark an invoice as paid."""
    invoice = get_object_or_404(Invoice, pk=pk)

    # Update the invoice status to paid
    invoice.status = "paid"
    invoice.payment_status = "paid"
    invoice.save()

    messages.success(
        request, f"Invoice {invoice.invoice_number} has been marked as paid."
    )
    return redirect("sales:invoice_detail", pk=pk)


@login_required
@require_POST
def invoice_mark_shipped(request, pk):
    """Quick action to mark an invoice as shipped."""
    invoice = get_object_or_404(Invoice, pk=pk)

    # Update the invoice shipping status to shipped
    invoice.shipping_status = "shipped"
    invoice.save()

    messages.success(
        request, f"Invoice {invoice.invoice_number} has been marked as shipped."
    )
    return redirect("sales:invoice_detail", pk=pk)


class InvoicePDFView(StaffRequiredMixin, DetailView):
    model = Invoice

    def get(self, request, *args, **kwargs):
        invoice = self.get_object()
        # TODO: Implement PDF generation
        messages.info(request, "PDF generation not implemented yet")
        return redirect("sales:invoice_detail", pk=invoice.pk)


# Invoice Item Views
class InvoiceItemCreateView(StaffRequiredMixin, CreateView):
    model = InvoiceItem
    fields = ["product", "description", "quantity", "unit_price", "discount_percent"]
    template_name = "sales/invoice_item_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = get_object_or_404(Invoice, pk=self.kwargs["invoice_pk"])
        return context

    def form_valid(self, form):
        invoice = get_object_or_404(Invoice, pk=self.kwargs["invoice_pk"])
        form.instance.invoice = invoice

        # If product is selected, auto-fill description
        if form.instance.product and not form.instance.description:
            form.instance.description = form.instance.product.name

        response = super().form_valid(form)
        messages.success(self.request, "Item added to invoice!")
        return response

    def get_success_url(self):
        return reverse("sales:invoice_detail", kwargs={"pk": self.kwargs["invoice_pk"]})


class InvoiceItemUpdateView(StaffRequiredMixin, UpdateView):
    model = InvoiceItem
    fields = ["product", "description", "quantity", "unit_price", "discount_percent"]
    template_name = "sales/invoice_item_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.object.invoice
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Invoice item updated!")
        return response

    def get_success_url(self):
        return reverse("sales:invoice_detail", kwargs={"pk": self.object.invoice.pk})


class InvoiceItemDeleteView(StaffRequiredMixin, DeleteView):
    model = InvoiceItem
    template_name = "sales/invoice_item_confirm_delete.html"

    def get_success_url(self):
        messages.success(self.request, "Item removed from invoice!")
        return reverse("sales:invoice_detail", kwargs={"pk": self.object.invoice.pk})


# Payment Views
class PaymentCreateView(StaffRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = "sales/payment_form_daisyui.html"

    def get_initial(self):
        initial = super().get_initial()
        invoice = get_object_or_404(Invoice, pk=self.kwargs["invoice_pk"])
        initial["invoice"] = invoice
        initial["customer"] = invoice.customer
        # Set the amount to the balance due (what's left to pay)
        initial["amount"] = invoice.balance_due
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = get_object_or_404(Invoice, pk=self.kwargs["invoice_pk"])
        return context

    def form_valid(self, form):
        invoice = get_object_or_404(Invoice, pk=self.kwargs["invoice_pk"])
        form.instance.invoice = invoice
        form.instance.customer = invoice.customer
        response = super().form_valid(form)

        # Update invoice paid amount and balance due
        from django.db.models import Sum

        total_paid = Payment.objects.filter(
            invoice=invoice, status="completed"
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        # Round to 2 decimal places
        from decimal import ROUND_HALF_UP

        invoice.paid_amount = total_paid.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        invoice.balance_due = (invoice.total_amount - total_paid).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Update invoice status based on payment
        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = "paid"
        elif invoice.paid_amount > 0:
            invoice.status = "partial"

        invoice.save()

        # Post payment to accounting ledger if status is completed
        if form.instance.status == "completed":
            try:
                # Import accounting service
                from accounting.services import post_incoming_payment
                from customer.models import Organization as Company
                
                # Get or create company (using first company for now)
                try:
                    company = Company.objects.first()
                    if not company:
                        company = Company.objects.create(
                            name="Default Company",
                            code="DEFAULT"
                        )
                except:
                    company = None
                
                # Set required fields for posting
                payment = form.instance
                payment.company = company
                payment.date = payment.payment_date
                payment.sale = invoice  # Map invoice to sale for the service
                
                # Post to ledger
                journal_entry = post_incoming_payment(payment)
                
                messages.info(
                    self.request, 
                    f"Payment posted to accounting ledger (Journal Entry #{journal_entry.pk})"
                )
            except Exception as e:
                messages.warning(
                    self.request,
                    f"Payment recorded but could not post to ledger: {str(e)}"
                )

        messages.success(
            self.request, f"Payment of ${form.instance.amount} recorded successfully!"
        )
        return response

    def get_success_url(self):
        return reverse("sales:invoice_detail", kwargs={"pk": self.kwargs["invoice_pk"]})


class PaymentDetailView(StaffRequiredMixin, DetailView):
    model = Payment
    template_name = "sales/payment_detail.html"


class PaymentUpdateView(StaffRequiredMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = "sales/payment_form_daisyui.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add invoice to context for the template
        context["invoice"] = self.object.invoice
        return context

    def get_success_url(self):
        return reverse_lazy("sales:payment_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        # Check if status changed to completed
        old_status = Payment.objects.get(pk=self.object.pk).status
        new_status = form.instance.status
        
        messages.success(
            self.request,
            f"Payment {form.instance.payment_number} has been updated successfully.",
        )
        response = super().form_valid(form)

        # Post to ledger if status changed to completed
        if old_status != "completed" and new_status == "completed":
            try:
                # Import accounting service
                from accounting.services import post_incoming_payment
                from customer.models import Organization as Company
                
                # Get or create company
                try:
                    company = Company.objects.first()
                    if not company:
                        company = Company.objects.create(
                            name="Default Company",
                            code="DEFAULT"
                        )
                except:
                    company = None
                
                # Set required fields for posting
                payment = form.instance
                payment.company = company
                payment.date = payment.payment_date
                payment.sale = payment.invoice  # Map invoice to sale
                
                # Post to ledger
                journal_entry = post_incoming_payment(payment)
                
                messages.info(
                    self.request, 
                    f"Payment posted to accounting ledger (Journal Entry #{journal_entry.pk})"
                )
            except Exception as e:
                messages.warning(
                    self.request,
                    f"Payment updated but could not post to ledger: {str(e)}"
                )

        # Update invoice payment status if needed
        if form.instance.invoice:
            invoice = form.instance.invoice

            # Recalculate total paid amount
            from django.db.models import Sum
            from decimal import Decimal

            total_paid = Payment.objects.filter(
                invoice=invoice, status="completed"
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            # Round to 2 decimal places
            from decimal import ROUND_HALF_UP

            invoice.paid_amount = total_paid.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            invoice.balance_due = (invoice.total_amount - total_paid).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Update invoice status based on payment
            if invoice.paid_amount >= invoice.total_amount:
                invoice.status = "paid"
            elif invoice.paid_amount > 0:
                invoice.status = "partial"
            else:
                invoice.status = "unpaid"

            invoice.save()

        return response


class PaymentDeleteView(StaffRequiredMixin, DeleteView):
    model = Payment
    template_name = "sales/payment_confirm_delete.html"

    def get_success_url(self):
        if self.object.invoice:
            return reverse_lazy(
                "sales:invoice_detail", kwargs={"pk": self.object.invoice.pk}
            )
        return reverse_lazy("sales:invoice_list")

    def delete(self, request, *args, **kwargs):
        payment = self.get_object()
        invoice = payment.invoice
        payment_number = payment.payment_number

        response = super().delete(request, *args, **kwargs)

        # Update invoice payment status after deletion
        if invoice:
            from django.db.models import Sum
            from decimal import Decimal

            total_paid = Payment.objects.filter(
                invoice=invoice, status="completed"
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

            # Round to 2 decimal places
            from decimal import ROUND_HALF_UP

            invoice.paid_amount = total_paid.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            invoice.balance_due = (invoice.total_amount - total_paid).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Update invoice status
            if invoice.paid_amount >= invoice.total_amount:
                invoice.status = "paid"
            elif invoice.paid_amount > 0:
                invoice.status = "partial"
            else:
                invoice.status = "unpaid"

            invoice.save()

        messages.success(
            request, f"Payment {payment_number} has been deleted successfully."
        )
        return response


# Shipment Views
class ShipmentListView(StaffRequiredMixin, ListView):
    model = InvoiceShipment
    template_name = "sales/shipment_list.html"
    context_object_name = "shipments"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super().get_queryset().select_related("invoice__customer", "supplier")
        )

        # Search functionality
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(shipment_number__icontains=search)
                | Q(tracking_number__icontains=search)
                | Q(invoice__invoice_number__icontains=search)
                | Q(invoice__customer__first_name__icontains=search)
                | Q(invoice__customer__last_name__icontains=search)
            )

        # Status filter
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by("-created_at")


class ShipmentDetailView(StaffRequiredMixin, DetailView):
    model = InvoiceShipment
    template_name = "sales/shipment_detail.html"
    context_object_name = "shipment"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["items"] = self.object.items.select_related("invoice_item__product")
        return context


# 2-Step Shipment Creation Views
class ShipmentCreateStep1View(StaffRequiredMixin, TemplateView):
    template_name = "sales/shipment_create_step1.html"

    def dispatch(self, request, *args, **kwargs):
        # Ensure invoice exists
        if "invoice_pk" not in self.kwargs:
            messages.error(request, "Invoice parameter is required")
            return redirect("sales:invoice_list")

        self.invoice = get_object_or_404(Invoice, pk=self.kwargs["invoice_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.invoice
        context["form"] = InvoiceShipmentForm(invoice=self.invoice)

        # Get customer addresses for shipping address selection
        if self.invoice.customer:
            # Get all shipping addresses for the customer
            customer_addresses = (
                self.invoice.customer.addresses.filter(is_active=True)
                .filter(Q(address_type="shipping") | Q(address_type="both"))
                .order_by("-is_default", "label")
            )

            context["customer_addresses"] = customer_addresses
            context["default_address"] = self.invoice.customer.get_default_address

        return context

    def post(self, request, *args, **kwargs):
        form = InvoiceShipmentForm(request.POST, invoice=self.invoice)

        # Store shipment data in session
        shipment_data = {
            "invoice_pk": self.kwargs["invoice_pk"],
            "supplier": request.POST.get("supplier"),
            "carrier": request.POST.get("carrier"),
            "service_type": request.POST.get("service_type"),
            "tracking_number": request.POST.get("tracking_number"),
            "tracking_url": request.POST.get("tracking_url"),
            "status": request.POST.get("status"),
            "package_count": request.POST.get("package_count"),
            "total_weight": request.POST.get("total_weight"),
            "shipping_cost": request.POST.get("shipping_cost"),
            "insurance_amount": request.POST.get("insurance_amount"),
            "internal_notes": request.POST.get("internal_notes"),
            "shipping_address_id": request.POST.get("shipping_address"),
            # Manual address fields
            "ship_to_name": request.POST.get("ship_to_name"),
            "ship_to_company": request.POST.get("ship_to_company"),
            "ship_to_address_line1": request.POST.get("ship_to_address_line1"),
            "ship_to_address_line2": request.POST.get("ship_to_address_line2"),
            "ship_to_city": request.POST.get("ship_to_city"),
            "ship_to_state": request.POST.get("ship_to_state"),
            "ship_to_postal_code": request.POST.get("ship_to_postal_code"),
            "ship_to_country": request.POST.get("ship_to_country"),
            "ship_to_phone": request.POST.get("ship_to_phone"),
            "ship_to_email": request.POST.get("ship_to_email"),
        }

        request.session["shipment_data"] = shipment_data
        return redirect(
            "sales:shipment_create_step2", invoice_pk=self.kwargs["invoice_pk"]
        )


class ShipmentCreateStep2View(StaffRequiredMixin, TemplateView):
    template_name = "sales/shipment_create_step2.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if step 1 data exists in session
        if "shipment_data" not in request.session:
            messages.warning(request, "Please complete the basic information first")
            return redirect(
                "sales:shipment_create_step1", invoice_pk=self.kwargs["invoice_pk"]
            )

        # Ensure invoice exists
        if "invoice_pk" not in self.kwargs:
            messages.error(request, "Invoice parameter is required")
            return redirect("sales:invoice_list")

        self.invoice = get_object_or_404(Invoice, pk=self.kwargs["invoice_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.invoice

        # Get invoice items with calculated quantities
        invoice_items = []
        for item in self.invoice.items.select_related("product").all():
            # Calculate total shipped quantity for this item
            total_shipped = ShipmentItem.objects.filter(invoice_item=item).aggregate(
                total=Sum("quantity_shipped")
            )["total"] or Decimal("0")

            # Calculate remaining quantity
            remaining = item.quantity - total_shipped

            # Add calculated fields to item
            item.shipped_quantity = total_shipped
            item.remaining_quantity = remaining

            if remaining > 0:
                invoice_items.append(item)

        context["invoice_items"] = invoice_items

        # Get shipment data from session
        shipment_data = self.request.session.get("shipment_data", {})
        context["shipment_data"] = shipment_data

        return context

    def post(self, request, *args, **kwargs):
        shipment_data = request.session.get("shipment_data", {})

        # Get selected items and quantities
        selected_items = request.POST.getlist("selected_items")

        if not selected_items:
            messages.error(request, "Please select at least one item to ship")
            return redirect(
                "sales:shipment_create_step2", invoice_pk=self.kwargs["invoice_pk"]
            )

        # Create shipment
        with transaction.atomic():
            shipment = InvoiceShipment()
            shipment.invoice = self.invoice

            # Apply basic data from session
            if shipment_data.get("supplier"):
                from purchases.models import Supplier

                try:
                    shipment.supplier = Supplier.objects.get(
                        pk=shipment_data["supplier"]
                    )
                except Supplier.DoesNotExist:
                    pass

            shipment.carrier = shipment_data.get("carrier", "ups")
            shipment.service_type = shipment_data.get("service_type", "")
            shipment.tracking_number = shipment_data.get("tracking_number", "")
            shipment.tracking_url = shipment_data.get("tracking_url", "")
            shipment.status = shipment_data.get("status", "pending")

            # Package details
            if shipment_data.get("package_count"):
                try:
                    shipment.package_count = int(shipment_data["package_count"])
                except:
                    pass
            if shipment_data.get("total_weight"):
                try:
                    shipment.total_weight = Decimal(str(shipment_data["total_weight"]))
                except:
                    pass
            if shipment_data.get("shipping_cost"):
                try:
                    shipment.shipping_cost = Decimal(
                        str(shipment_data["shipping_cost"])
                    )
                except:
                    pass
            if shipment_data.get("insurance_amount"):
                try:
                    shipment.insurance_amount = Decimal(
                        str(shipment_data["insurance_amount"])
                    )
                except:
                    pass

            shipment.internal_notes = shipment_data.get("internal_notes", "")

            # Handle shipping address
            shipping_address_id = shipment_data.get("shipping_address_id")
            if shipping_address_id and self.invoice.customer:
                try:
                    selected_address = CustomerAddress.objects.get(
                        id=shipping_address_id,
                        customer=self.invoice.customer,
                        is_active=True,
                    )
                    shipment.ship_to_name = selected_address.recipient_name
                    shipment.ship_to_company = selected_address.company_name or ""
                    shipment.ship_to_address_line1 = selected_address.address_line1
                    shipment.ship_to_address_line2 = (
                        selected_address.address_line2 or ""
                    )
                    shipment.ship_to_city = selected_address.city
                    shipment.ship_to_state = selected_address.state
                    shipment.ship_to_postal_code = selected_address.postal_code
                    shipment.ship_to_country = selected_address.country
                    shipment.ship_to_phone = selected_address.phone or ""
                    shipment.ship_to_email = self.invoice.customer.email or ""
                except CustomerAddress.DoesNotExist:
                    pass
            else:
                # Use manual address fields
                shipment.ship_to_name = shipment_data.get("ship_to_name", "")
                shipment.ship_to_company = shipment_data.get("ship_to_company", "")
                shipment.ship_to_address_line1 = shipment_data.get(
                    "ship_to_address_line1", ""
                )
                shipment.ship_to_address_line2 = shipment_data.get(
                    "ship_to_address_line2", ""
                )
                shipment.ship_to_city = shipment_data.get("ship_to_city", "")
                shipment.ship_to_state = shipment_data.get("ship_to_state", "")
                shipment.ship_to_postal_code = shipment_data.get(
                    "ship_to_postal_code", ""
                )
                shipment.ship_to_country = shipment_data.get("ship_to_country", "")
                shipment.ship_to_phone = shipment_data.get("ship_to_phone", "")
                shipment.ship_to_email = shipment_data.get("ship_to_email", "")

            # Save shipment
            shipment.save()

            # Create shipment items
            for item_id in selected_items:
                quantity_field = f"quantity_{item_id}"
                notes_field = f"notes_{item_id}"

                quantity = request.POST.get(quantity_field)
                notes = request.POST.get(notes_field, "")

                if quantity:
                    try:
                        invoice_item = InvoiceItem.objects.get(pk=item_id)
                        ShipmentItem.objects.create(
                            shipment=shipment,
                            invoice_item=invoice_item,
                            quantity_shipped=Decimal(quantity),
                            notes=notes,
                        )
                    except (InvoiceItem.DoesNotExist, ValueError):
                        pass

        # Clear session data
        if "shipment_data" in request.session:
            del request.session["shipment_data"]

        messages.success(
            request, f"Shipment {shipment.shipment_number} created successfully!"
        )
        return redirect("sales:invoice_detail", pk=self.invoice.pk)


# 2-Step Shipment Edit Views
class ShipmentEditStep1View(StaffRequiredMixin, TemplateView):
    template_name = "sales/shipment_edit_step1.html"

    def dispatch(self, request, *args, **kwargs):
        # Ensure shipment exists
        if "pk" not in self.kwargs:
            messages.error(request, "Shipment parameter is required")
            return redirect("sales:shipment_list")

        self.shipment = get_object_or_404(InvoiceShipment, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shipment"] = self.shipment
        context["invoice"] = self.shipment.invoice
        context["form"] = InvoiceShipmentForm(instance=self.shipment)

        # Add suppliers for the dropdown
        from purchases.models import Supplier

        context["suppliers"] = Supplier.objects.filter(is_active=True).order_by("name")

        # Get customer addresses for shipping address selection
        if self.shipment.invoice and self.shipment.invoice.customer:
            context["customer_addresses"] = (
                self.shipment.invoice.customer.addresses.filter(is_active=True)
                .filter(Q(address_type="shipping") | Q(address_type="both"))
                .order_by("-is_default", "label")
            )
            context["default_address"] = (
                self.shipment.invoice.customer.get_default_address
            )

            # Check if current shipping address matches any customer address
            context["current_address_id"] = None
            for address in context["customer_addresses"]:
                if (
                    address.recipient_name == self.shipment.ship_to_name
                    and address.address_line1 == self.shipment.ship_to_address_line1
                    and address.city == self.shipment.ship_to_city
                    and address.state == self.shipment.ship_to_state
                ):
                    context["current_address_id"] = address.id
                    break

        return context

    def post(self, request, *args, **kwargs):
        # Store shipment update data in session
        shipment_data = {
            "shipment_pk": self.kwargs["pk"],
            "supplier": request.POST.get("supplier"),
            "carrier": request.POST.get("carrier"),
            "service_type": request.POST.get("service_type"),
            "tracking_number": request.POST.get("tracking_number"),
            "tracking_url": request.POST.get("tracking_url"),
            "status": request.POST.get("status"),
            "package_count": request.POST.get("package_count"),
            "total_weight": request.POST.get("total_weight"),
            "shipping_cost": request.POST.get("shipping_cost"),
            "insurance_amount": request.POST.get("insurance_amount"),
            "ship_date": request.POST.get("ship_date"),
            "estimated_delivery": request.POST.get("estimated_delivery"),
            "actual_delivery": request.POST.get("actual_delivery"),
            "delivered_to": request.POST.get("delivered_to"),
            "delivery_signature": request.POST.get("delivery_signature"),
            "delivery_notes": request.POST.get("delivery_notes"),
            "internal_notes": request.POST.get("internal_notes"),
            "shipping_address_id": request.POST.get("shipping_address"),
            # Manual address fields
            "ship_to_name": request.POST.get("ship_to_name"),
            "ship_to_company": request.POST.get("ship_to_company"),
            "ship_to_address_line1": request.POST.get("ship_to_address_line1"),
            "ship_to_address_line2": request.POST.get("ship_to_address_line2"),
            "ship_to_city": request.POST.get("ship_to_city"),
            "ship_to_state": request.POST.get("ship_to_state"),
            "ship_to_postal_code": request.POST.get("ship_to_postal_code"),
            "ship_to_country": request.POST.get("ship_to_country"),
            "ship_to_phone": request.POST.get("ship_to_phone"),
            "ship_to_email": request.POST.get("ship_to_email"),
        }

        request.session["shipment_edit_data"] = shipment_data
        return redirect("sales:shipment_edit_step2", pk=self.kwargs["pk"])


class ShipmentEditStep2View(StaffRequiredMixin, TemplateView):
    template_name = "sales/shipment_edit_step2.html"

    def dispatch(self, request, *args, **kwargs):
        # Check if step 1 data exists in session
        if "shipment_edit_data" not in request.session:
            messages.warning(request, "Please complete the basic information first")
            return redirect("sales:shipment_edit_step1", pk=self.kwargs["pk"])

        # Ensure shipment exists
        if "pk" not in self.kwargs:
            messages.error(request, "Shipment parameter is required")
            return redirect("sales:shipment_list")

        self.shipment = get_object_or_404(InvoiceShipment, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shipment"] = self.shipment
        context["invoice"] = self.shipment.invoice

        # Get invoice items with calculated quantities
        invoice_items = []
        selected_item_ids = []

        for item in self.shipment.invoice.items.select_related("product").filter(
            product__isnull=False
        ):
            # Calculate total shipped quantity for this item across all shipments
            total_shipped = ShipmentItem.objects.filter(invoice_item=item).aggregate(
                total=Sum("quantity_shipped")
            )["total"] or Decimal("0")

            # Calculate remaining quantity
            remaining = item.quantity - total_shipped

            # Get current shipment quantity for this item
            current_shipment_quantity = 0
            shipment_item = ShipmentItem.objects.filter(
                shipment=self.shipment, invoice_item=item
            ).first()
            if shipment_item:
                current_shipment_quantity = shipment_item.quantity_shipped
                selected_item_ids.append(item.id)

            # Add calculated fields to item
            item.shipped_quantity = total_shipped
            item.remaining_quantity = remaining
            item.current_shipment_quantity = current_shipment_quantity
            item.max_quantity = (
                remaining + current_shipment_quantity
            )  # Max they can ship including what's already in this shipment
            item.notes = shipment_item.notes if shipment_item else ""

            invoice_items.append(item)

        context["invoice_items"] = invoice_items
        context["selected_item_ids"] = selected_item_ids

        # Get shipment data from session
        shipment_data = self.request.session.get("shipment_edit_data", {})
        context["shipment_data"] = shipment_data

        # Create formset for existing shipment items
        if self.request.POST:
            context["formset"] = ShipmentItemFormSet(
                self.request.POST, instance=self.shipment
            )
        else:
            context["formset"] = ShipmentItemFormSet(instance=self.shipment)

        return context

    def post(self, request, *args, **kwargs):
        shipment_data = request.session.get("shipment_edit_data", {})

        # Get selected items and quantities
        selected_items = request.POST.getlist("selected_items")

        # Update shipment
        with transaction.atomic():
            shipment = self.shipment

            # Apply basic data from session
            if shipment_data.get("supplier"):
                from purchases.models import Supplier

                try:
                    shipment.supplier = Supplier.objects.get(
                        pk=shipment_data["supplier"]
                    )
                except Supplier.DoesNotExist:
                    shipment.supplier = None
            else:
                shipment.supplier = None

            shipment.carrier = shipment_data.get("carrier", "ups")
            shipment.service_type = shipment_data.get("service_type", "")
            shipment.tracking_number = shipment_data.get("tracking_number", "")
            shipment.tracking_url = shipment_data.get("tracking_url", "")
            shipment.status = shipment_data.get("status", "pending")

            # Package details
            if shipment_data.get("package_count"):
                try:
                    shipment.package_count = int(shipment_data["package_count"])
                except:
                    pass
            if shipment_data.get("total_weight"):
                try:
                    shipment.total_weight = Decimal(str(shipment_data["total_weight"]))
                except:
                    pass
            if shipment_data.get("shipping_cost"):
                try:
                    shipment.shipping_cost = Decimal(
                        str(shipment_data["shipping_cost"])
                    )
                except:
                    pass
            if shipment_data.get("insurance_amount"):
                try:
                    shipment.insurance_amount = Decimal(
                        str(shipment_data["insurance_amount"])
                    )
                except:
                    pass

            shipment.internal_notes = shipment_data.get("internal_notes", "")

            # Save shipment
            shipment.save()

            # Clear existing shipment items
            ShipmentItem.objects.filter(shipment=shipment).delete()

            # Create new shipment items
            for item_id in selected_items:
                quantity_field = f"quantity_{item_id}"
                notes_field = f"notes_{item_id}"

                quantity = request.POST.get(quantity_field)
                notes = request.POST.get(notes_field, "")

                if quantity:
                    try:
                        invoice_item = InvoiceItem.objects.get(pk=item_id)
                        ShipmentItem.objects.create(
                            shipment=shipment,
                            invoice_item=invoice_item,
                            quantity_shipped=Decimal(quantity),
                            notes=notes,
                        )
                    except (InvoiceItem.DoesNotExist, ValueError):
                        pass

        # Clear session data
        if "shipment_edit_data" in request.session:
            del request.session["shipment_edit_data"]

        messages.success(
            request, f"Shipment {shipment.shipment_number} updated successfully!"
        )
        return redirect("sales:shipment_detail", pk=shipment.pk)


# Legacy Single-Step Shipment Creation
class ShipmentCreateView(StaffRequiredMixin, CreateView):
    model = InvoiceShipment
    form_class = InvoiceShipmentForm
    template_name = "sales/shipment_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = get_object_or_404(Invoice, pk=self.kwargs["invoice_pk"])
        context["invoice"] = invoice

        if self.request.POST:
            context["formset"] = ShipmentItemFormSet(
                self.request.POST, form_kwargs={"invoice": invoice}
            )
        else:
            # Pre-populate formset with invoice items
            initial = []
            for item in invoice.items.all():
                # Calculate already shipped quantity
                shipped = (
                    ShipmentItem.objects.filter(invoice_item=item).aggregate(
                        total=Sum("quantity_shipped")
                    )["total"]
                    or 0
                )

                remaining = item.quantity - shipped
                if remaining > 0:
                    initial.append(
                        {"invoice_item": item, "quantity_shipped": remaining}
                    )

            context["formset"] = ShipmentItemFormSet(
                initial=initial, form_kwargs={"invoice": invoice}
            )

        # Get or calculate next shipment number for this invoice
        existing_shipments = invoice.shipments.count()
        context["suggested_shipment_number"] = (
            f"{invoice.invoice_number}-S{existing_shipments + 1:02d}"
        )

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            invoice = get_object_or_404(Invoice, pk=self.kwargs["invoice_pk"])
            self.object = form.save(commit=False)
            self.object.invoice = invoice
            self.object.save()

            # Save formset
            formset.instance = self.object
            formset.save()

            messages.success(
                self.request,
                f"Shipment {self.object.shipment_number} created successfully!",
            )
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        if self.object.invoice:
            return reverse(
                "sales:invoice_detail", kwargs={"pk": self.object.invoice.pk}
            )
        return reverse("sales:shipment_detail", kwargs={"pk": self.object.pk})


class ShipmentUpdateView(StaffRequiredMixin, UpdateView):
    model = InvoiceShipment
    form_class = InvoiceShipmentForm
    template_name = "sales/shipment_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.object.invoice

        if self.request.POST:
            context["formset"] = ShipmentItemFormSet(
                self.request.POST,
                instance=self.object,
                form_kwargs={"shipment": self.object},
            )
        else:
            context["formset"] = ShipmentItemFormSet(
                instance=self.object, form_kwargs={"shipment": self.object}
            )

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Shipment updated successfully!")
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        if self.object.invoice:
            return reverse(
                "sales:invoice_detail", kwargs={"pk": self.object.invoice.pk}
            )
        return reverse("sales:shipment_detail", kwargs={"pk": self.object.pk})


class ShipmentDeleteView(StaffRequiredMixin, DeleteView):
    model = InvoiceShipment
    template_name = "sales/shipment_confirm_delete.html"

    def get_success_url(self):
        invoice_id = self.object.invoice.pk if self.object.invoice else None
        if invoice_id:
            return reverse("sales:invoice_detail", kwargs={"pk": invoice_id})
        return reverse_lazy("sales:shipment_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Shipment deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Shipment Item Views
class ShipmentItemCreateView(StaffRequiredMixin, CreateView):
    model = ShipmentItem
    fields = ["invoice_item", "quantity_shipped", "serial_numbers", "notes"]
    template_name = "sales/shipment_item_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shipment = get_object_or_404(InvoiceShipment, pk=self.kwargs["shipment_pk"])
        context["shipment"] = shipment
        return context

    def form_valid(self, form):
        shipment = get_object_or_404(InvoiceShipment, pk=self.kwargs["shipment_pk"])
        form.instance.shipment = shipment

        # Validate that invoice item belongs to the shipment's invoice
        if form.instance.invoice_item.invoice != shipment.invoice:
            form.add_error(
                "invoice_item", "Selected item does not belong to this invoice"
            )
            return self.form_invalid(form)

        # Validate quantity doesn't exceed invoice item quantity
        total_shipped = (
            ShipmentItem.objects.filter(invoice_item=form.instance.invoice_item)
            .exclude(pk=form.instance.pk)
            .aggregate(total=Sum("quantity_shipped"))["total"]
            or 0
        )

        if (
            total_shipped + form.instance.quantity_shipped
            > form.instance.invoice_item.quantity
        ):
            form.add_error("quantity_shipped", "Quantity exceeds available amount")
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(self.request, "Item added to shipment successfully!")
        return response

    def get_success_url(self):
        return reverse(
            "sales:shipment_detail", kwargs={"pk": self.kwargs["shipment_pk"]}
        )


class ShipmentItemUpdateView(StaffRequiredMixin, UpdateView):
    model = ShipmentItem
    fields = ["invoice_item", "quantity_shipped", "serial_numbers", "notes"]
    template_name = "sales/shipment_item_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shipment"] = self.object.shipment
        return context

    def form_valid(self, form):
        # Validate quantity doesn't exceed invoice item quantity
        total_shipped = (
            ShipmentItem.objects.filter(invoice_item=form.instance.invoice_item)
            .exclude(pk=form.instance.pk)
            .aggregate(total=Sum("quantity_shipped"))["total"]
            or 0
        )

        if (
            total_shipped + form.instance.quantity_shipped
            > form.instance.invoice_item.quantity
        ):
            form.add_error("quantity_shipped", "Quantity exceeds available amount")
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(self.request, "Shipment item updated successfully!")
        return response

    def get_success_url(self):
        return reverse("sales:shipment_detail", kwargs={"pk": self.object.shipment.pk})


class ShipmentItemDeleteView(StaffRequiredMixin, DeleteView):
    model = ShipmentItem
    template_name = "sales/shipment_item_confirm_delete.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shipment"] = self.object.shipment
        return context

    def get_success_url(self):
        return reverse("sales:shipment_detail", kwargs={"pk": self.object.shipment.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Item removed from shipment!")
        return super().delete(request, *args, **kwargs)


# API Views
class AvailableInventoryAPIView(StaffRequiredMixin, View):
    def get(self, request, product_id):
        """Get available inventory for a product that can be sold"""
        try:
            product = Product.objects.get(pk=product_id)

            # Get inventory that is available for sale
            available_inventory = Inventory.objects.filter(
                product=product, status="available"
            ).values("id", "serial_number", "location")

            return JsonResponse(
                {
                    "success": True,
                    "inventory": list(available_inventory),
                    "count": available_inventory.count(),
                }
            )
        except Product.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Product not found"}, status=404
            )
