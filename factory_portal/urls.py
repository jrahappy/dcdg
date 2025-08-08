from django.urls import path
from . import views

app_name = 'factory_portal'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Work Orders
    path('work-orders/', views.work_order_list, name='work_order_list'),
    path('work-orders/<int:pk>/', views.work_order_detail, name='work_order_detail'),
    path('work-orders/<int:pk>/update-status/', views.update_work_order_status, name='update_work_order_status'),
    
    # Fulfillment Items
    path('work-orders/<int:work_order_pk>/items/<int:item_pk>/update/', 
         views.fulfillment_item_update, name='fulfillment_item_update'),
    
    # Shipments
    path('work-orders/<int:work_order_pk>/create-shipment/', 
         views.create_shipment, name='create_shipment'),
    path('shipments/', views.shipment_list, name='shipment_list'),
    
    # Supply Requests
    path('supply-requests/', views.supply_request_list, name='supply_request_list'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Packing Slip
    path('packing-slip/<int:invoice_id>/', views.packing_slip, name='packing_slip'),
    
    # Ship Order
    path('ship-order/', views.ship_order, name='ship_order'),
    
    # Create Invoice (Purchase Order)
    path('create-invoice/', views.create_invoice, name='create_invoice'),
    
    # View Billing Invoice (Purchase Order)
    path('billing-invoice/<int:po_id>/', views.view_billing_invoice, name='view_billing_invoice'),
]