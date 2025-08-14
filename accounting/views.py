from django.shortcuts import render
from django.db import models
from sales.models import Customer, Invoice, InvoiceItem, Payment
from product.models import Product, Category
from purchases.models import Supplier, PurchaseOrder, PurchaseOrderItem


def payment_view(request):
    payments = Payment.objects.all()
    return render(request, "accounting/payment_list.html", {"payments": payments})
