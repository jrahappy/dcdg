from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Quote URLs
    path('quotes/', views.QuoteListView.as_view(), name='quote_list'),
    path('quotes/create/', views.QuoteCreateView.as_view(), name='quote_create'),
    path('quotes/<int:pk>/', views.QuoteDetailView.as_view(), name='quote_detail'),
    path('quotes/<int:pk>/update/', views.QuoteUpdateView.as_view(), name='quote_update'),
    path('quotes/<int:pk>/delete/', views.QuoteDeleteView.as_view(), name='quote_delete'),
    
    # Quote Items
    path('quotes/<int:quote_pk>/items/add/', views.QuoteItemCreateView.as_view(), name='quote_item_add'),
    path('quotes/<int:quote_pk>/items/<int:pk>/edit/', views.QuoteItemUpdateView.as_view(), name='quote_item_edit'),
    path('quotes/<int:quote_pk>/items/<int:pk>/delete/', views.QuoteItemDeleteView.as_view(), name='quote_item_delete'),
    
    # Order URLs
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/update/', views.OrderUpdateView.as_view(), name='order_update'),
    path('orders/<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
    
    # Order Items
    path('orders/<int:order_pk>/items/add/', views.OrderItemCreateView.as_view(), name='order_item_add'),
    path('orders/<int:order_pk>/items/<int:pk>/edit/', views.OrderItemUpdateView.as_view(), name='order_item_edit'),
    path('orders/<int:order_pk>/items/<int:pk>/delete/', views.OrderItemDeleteView.as_view(), name='order_item_delete'),
    
    # Invoice URLs
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', views.InvoiceCreateStep1View.as_view(), name='invoice_create'),
    path('invoices/create/step1/', views.InvoiceCreateStep1View.as_view(), name='invoice_create_step1'),
    path('invoices/create/step2/', views.InvoiceCreateStep2View.as_view(), name='invoice_create_step2'),
    path('invoices/create/step3/', views.InvoiceCreateStep3View.as_view(), name='invoice_create_step3'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/update/', views.InvoiceUpdateView.as_view(), name='invoice_update'),
    path('invoices/<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='invoice_delete'),
    path('invoices/<int:pk>/send/', views.InvoiceSendView.as_view(), name='invoice_send'),
    path('invoices/<int:pk>/update-tracking/', views.invoice_update_tracking, name='invoice_update_tracking'),
    path('invoices/<int:pk>/pdf/', views.InvoicePDFView.as_view(), name='invoice_pdf'),
    
    # Invoice Items
    path('invoices/<int:invoice_pk>/items/add/', views.InvoiceItemCreateView.as_view(), name='invoice_item_add'),
    path('invoices/<int:invoice_pk>/items/<int:pk>/edit/', views.InvoiceItemUpdateView.as_view(), name='invoice_item_edit'),
    path('invoices/<int:invoice_pk>/items/<int:pk>/delete/', views.InvoiceItemDeleteView.as_view(), name='invoice_item_delete'),
    
    # Payment URLs
    path('invoices/<int:invoice_pk>/payments/add/', views.PaymentCreateView.as_view(), name='payment_add'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    
    # Shipment URLs
    path('shipments/', views.ShipmentListView.as_view(), name='shipment_list'),
    path('shipments/<int:pk>/', views.ShipmentDetailView.as_view(), name='shipment_detail'),
    path('shipments/<int:pk>/update/', views.ShipmentEditStep1View.as_view(), name='shipment_update'),
    path('shipments/<int:pk>/delete/', views.ShipmentDeleteView.as_view(), name='shipment_delete'),
    # 2-Step Shipment Creation
    path('invoices/<int:invoice_pk>/shipments/add/', views.ShipmentCreateStep1View.as_view(), name='shipment_add'),
    path('invoices/<int:invoice_pk>/shipments/create/step1/', views.ShipmentCreateStep1View.as_view(), name='shipment_create_step1'),
    path('invoices/<int:invoice_pk>/shipments/create/step2/', views.ShipmentCreateStep2View.as_view(), name='shipment_create_step2'),
    # 2-Step Shipment Editing
    path('shipments/<int:pk>/edit/step1/', views.ShipmentEditStep1View.as_view(), name='shipment_edit_step1'),
    path('shipments/<int:pk>/edit/step2/', views.ShipmentEditStep2View.as_view(), name='shipment_edit_step2'),
    # Legacy single-step shipment update/creation (if needed)
    path('shipments/<int:pk>/update-single/', views.ShipmentUpdateView.as_view(), name='shipment_update_single'),
    path('invoices/<int:invoice_pk>/shipments/add-single/', views.ShipmentCreateView.as_view(), name='shipment_add_single'),
    
    # Shipment Item URLs
    path('shipments/<int:shipment_pk>/items/add/', views.ShipmentItemCreateView.as_view(), name='shipment_item_add'),
    path('shipment-items/<int:pk>/update/', views.ShipmentItemUpdateView.as_view(), name='shipment_item_update'),
    path('shipment-items/<int:pk>/delete/', views.ShipmentItemDeleteView.as_view(), name='shipment_item_delete'),
    
    # API URLs
    path('api/inventory/available/<int:product_id>/', views.AvailableInventoryAPIView.as_view(), name='api_available_inventory'),
]