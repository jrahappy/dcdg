from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
from decimal import Decimal
import json

from product.models import Product, Category
from sales.models import Invoice, InvoiceItem
from .models import Cart, CartItem, ShippingRate, PromoCode


def get_cart(request):
    """Get or create cart for the current session"""
    if not request.session.session_key:
        request.session.create()

    cart, created = Cart.objects.get_or_create(
        session_key=request.session.session_key,
        defaults={"user": request.user if request.user.is_authenticated else None},
    )
    return cart


def product_list(request):
    """Display products for shopping"""
    queryset = Product.objects.filter(status="active").select_related("category").prefetch_related("images")

    # Search
    search = request.GET.get("search")
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(short_description__icontains=search)
            | Q(long_description__icontains=search)
            | Q(sku__icontains=search)
        )

    # Category filter
    category_id = request.GET.get("category")
    if category_id:
        try:
            category = Category.objects.get(pk=category_id, is_active=True)
            # Get all active descendant categories
            descendant_ids = [category.id]
            descendants = list(category.children.filter(is_active=True))
            while descendants:
                child = descendants.pop()
                descendant_ids.append(child.id)
                descendants.extend(list(child.children.filter(is_active=True)))
            queryset = queryset.filter(category_id__in=descendant_ids)
        except Category.DoesNotExist:
            pass

    # Sort
    sort = request.GET.get("sort", "-created_at")
    if sort in ["price", "-price", "name", "-name", "-created_at"]:
        queryset = queryset.order_by(sort)

    # Pagination
    paginator = Paginator(queryset, 12)
    page_number = request.GET.get("page")
    products = paginator.get_page(page_number)

    context = {
        "products": products,
        "categories": Category.objects.filter(parent__isnull=True, is_active=True),
        "cart": get_cart(request),
        "page_obj": products,
        "is_paginated": products.has_other_pages(),
    }

    return render(request, "shop/product_list.html", context)


def product_detail(request, pk):
    """Display single product detail"""
    product = get_object_or_404(Product, pk=pk, status="active")

    # Get product options with their items
    from product.models import ProductOption, ProductOptionItem

    product_options = ProductOption.objects.filter(
        product=product, is_active=True
    ).select_related("option_name")

    # Build options data structure with items
    options_data = []
    for option in product_options:
        items = ProductOptionItem.objects.filter(
            option_name=option.option_name, is_active=True
        ).order_by("ordering", "value")

        options_data.append(
            {"option": option, "name": option.option_name.name, "items": items}
        )

    # Get related products from same category
    related_products = Product.objects.filter(
        category=product.category, status="active"
    ).exclude(pk=product.pk)[:4]

    context = {
        "product": product,
        "related_products": related_products,
        "cart": get_cart(request),
        "product_options": options_data,
    }

    return render(request, "shop/product_detail.html", context)


def cart_view(request):
    """Display shopping cart"""
    cart = get_cart(request)

    # Handle AJAX requests for cart items
    if (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.GET.get("format") == "json"
    ):
        from django.template.loader import render_to_string

        cart_items_html = render_to_string("shop/cart_items.html", {"cart": cart})

        return JsonResponse(
            {
                "html": cart_items_html,
                "subtotal": float(cart.subtotal),
                "total_items": cart.total_items,
            }
        )

    return render(request, "shop/cart.html", {"cart": cart})


def add_to_cart(request, pk):
    """Add product to cart (AJAX)"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    product = get_object_or_404(Product, pk=pk, status="active")
    quantity = int(request.POST.get("quantity", 1))

    if quantity < 1:
        return JsonResponse({"error": "Invalid quantity"}, status=400)

    # Get selected options
    import json

    selected_options = {}
    options_json = request.POST.get("selected_options", "{}")
    try:
        selected_options = json.loads(options_json)
    except json.JSONDecodeError:
        pass

    # Validate that all required options are selected
    from product.models import ProductOption

    required_options = ProductOption.objects.filter(
        product=product, is_active=True
    ).select_related("option_name")

    for option in required_options:
        if option.option_name.name not in selected_options:
            return JsonResponse(
                {"error": f"Please select {option.option_name.name}"}, status=400
            )

    # Get or create cart
    cart = get_cart(request)

    # Try to find existing cart item with same product and options
    existing_item = None
    for item in cart.items.filter(product=product):
        if item.selected_options == selected_options:
            existing_item = item
            break

    if existing_item:
        # Update quantity if item with same options exists
        existing_item.quantity += quantity
        existing_item.save()
        cart_item = existing_item
    else:
        # Create new cart item
        cart_item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            unit_price=product.price,
            selected_options=selected_options,
        )

    return JsonResponse(
        {
            "success": True,
            "message": f"{product.name} added to cart",
            "cart_total_items": cart.total_items,
            "cart_subtotal": float(cart.subtotal),
        }
    )


def update_cart(request, pk):
    """Update cart item quantity (AJAX)"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    cart_item = get_object_or_404(CartItem, pk=pk)

    # Verify cart ownership
    if cart_item.cart.session_key != request.session.session_key:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    quantity = int(request.POST.get("quantity", 1))

    if quantity < 1:
        cart_item.delete()
        message = "Item removed from cart"
    else:
        cart_item.quantity = quantity
        cart_item.save()
        message = "Cart updated"

    cart = cart_item.cart

    return JsonResponse(
        {
            "success": True,
            "message": message,
            "cart_total_items": cart.total_items,
            "cart_subtotal": float(cart.subtotal),
            "item_total": float(cart_item.line_total) if quantity >= 1 else 0,
        }
    )


def remove_from_cart(request, pk):
    """Remove item from cart (AJAX)"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    cart_item = get_object_or_404(CartItem, pk=pk)

    # Verify cart ownership
    if cart_item.cart.session_key != request.session.session_key:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    cart = cart_item.cart
    cart_item.delete()

    return JsonResponse(
        {
            "success": True,
            "message": "Item removed from cart",
            "cart_total_items": cart.total_items,
            "cart_subtotal": float(cart.subtotal),
        }
    )


def checkout(request):
    """Checkout process"""
    cart = get_cart(request)

    if request.method == "GET":
        if not cart.items.exists():
            messages.warning(request, "Your cart is empty")
            return redirect("shop:product_list")

        # Get shipping rates
        shipping_rates = ShippingRate.objects.filter(is_active=True)

        # Get saved addresses for authenticated users
        saved_addresses = None
        if request.user.is_authenticated:
            from customer.models import CustomerAddress

            saved_addresses = CustomerAddress.objects.filter(
                user=request.user, is_active=True
            ).order_by("-is_default", "-created_at")

        context = {
            "cart": cart,
            "shipping_rates": shipping_rates,
            "saved_addresses": saved_addresses,
        }

        return render(request, "shop/checkout.html", context)

    elif request.method == "POST":
        if not cart.items.exists():
            return JsonResponse({"error": "Cart is empty"}, status=400)

        try:
            # Create invoice (shop order)
            invoice = Invoice.objects.create(
                user=request.user if request.user.is_authenticated else None,
                is_shop_order=True,
                email=request.POST.get("email"),
                first_name=request.POST.get("first_name"),
                last_name=request.POST.get("last_name"),
                phone=request.POST.get("phone", ""),
                billing_address_line1=request.POST.get("billing_address_line1"),
                billing_address_line2=request.POST.get("billing_address_line2", ""),
                billing_city=request.POST.get("billing_city"),
                billing_state=request.POST.get("billing_state"),
                billing_postal_code=request.POST.get("billing_postal_code"),
                billing_country=request.POST.get("billing_country", "US"),
                shipping_same_as_billing=request.POST.get("shipping_same_as_billing")
                == "on",
                notes=request.POST.get("notes", ""),
                invoice_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=30),
                status="sent",  # Shop orders start as sent
            )

            # If shipping address is different
            if not invoice.shipping_same_as_billing:
                invoice.shipping_address_line1 = request.POST.get(
                    "shipping_address_line1"
                )
                invoice.shipping_address_line2 = request.POST.get(
                    "shipping_address_line2", ""
                )
                invoice.shipping_city = request.POST.get("shipping_city")
                invoice.shipping_state = request.POST.get("shipping_state")
                invoice.shipping_postal_code = request.POST.get("shipping_postal_code")
                invoice.shipping_country = request.POST.get("shipping_country", "US")

            # Add shipping cost
            shipping_rate_id = request.POST.get("shipping_rate")
            if shipping_rate_id:
                try:
                    shipping_rate = ShippingRate.objects.get(
                        pk=shipping_rate_id, is_active=True
                    )
                    cost = shipping_rate.calculate_cost(cart.subtotal, cart.total_items)
                    if cost is not None:
                        invoice.shipping_cost = cost
                except ShippingRate.DoesNotExist:
                    pass

            # Apply promo code if provided
            promo_code = request.POST.get("promo_code")
            if promo_code:
                try:
                    promo = PromoCode.objects.get(code__iexact=promo_code)
                    if promo.is_valid():
                        invoice.discount_amount = promo.calculate_discount(
                            cart.subtotal
                        )
                        promo.used_count += 1
                        promo.save()
                except PromoCode.DoesNotExist:
                    pass

            invoice.save()

            # Create invoice items
            for cart_item in cart.items.all():
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product=cart_item.product,
                    description=cart_item.product.name,
                    product_options=cart_item.selected_options,  # Pass product options
                    quantity=cart_item.quantity,
                    unit_price=cart_item.unit_price,
                )

            # Calculate totals
            invoice.calculate_totals()

            # Clear cart
            cart.clear()

            # Store order tracking code in session for anonymous users
            if not request.user.is_authenticated:
                request.session["last_order_tracking"] = str(invoice.tracking_code)

            return JsonResponse(
                {
                    "success": True,
                    "order_number": invoice.invoice_number,
                    "tracking_code": str(invoice.tracking_code),
                    "redirect_url": f"/shop/order/success/{invoice.tracking_code}/",
                }
            )
        except Exception as e:
            # Log the error for debugging
            import traceback

            print(f"Checkout error: {str(e)}")
            print(traceback.format_exc())

            return JsonResponse(
                {
                    "success": False,
                    "error": f"An error occurred during checkout: {str(e)}",
                },
                status=500,
            )


def order_success(request, tracking_code):
    """Order success page"""
    try:
        order = Invoice.objects.get(tracking_code=tracking_code, is_shop_order=True)
    except Invoice.DoesNotExist:
        order = None

    return render(request, "shop/order_success.html", {"order": order})


def order_tracking(request):
    """Track order by tracking code"""
    if request.method == "GET":
        return render(request, "shop/order_tracking.html")

    elif request.method == "POST":
        tracking_code = request.POST.get("tracking_code")
        email = request.POST.get("email")

        try:
            order = Invoice.objects.get(
                tracking_code=tracking_code, email__iexact=email, is_shop_order=True
            )
            return render(request, "shop/order_detail.html", {"order": order})
        except Invoice.DoesNotExist:
            messages.error(
                request, "Order not found. Please check your tracking code and email."
            )
            return render(request, "shop/order_tracking.html")
