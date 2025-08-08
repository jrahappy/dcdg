from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    # Purchase Order URLs
    path('', views.purchase_order_list, name='purchase_order_list'),
    path('orders/create/', views.PurchaseOrderCreateStep1View.as_view(), name='purchase_order_create'),
    path('orders/create/step1/', views.PurchaseOrderCreateStep1View.as_view(), name='purchase_order_create_step1'),
    path('orders/create/step2/', views.PurchaseOrderCreateStep2View.as_view(), name='purchase_order_create_step2'),
    path('orders/create/step3/', views.PurchaseOrderCreateStep3View.as_view(), name='purchase_order_create_step3'),
    path('orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('orders/<int:pk>/edit/', views.PurchaseOrderEditStep1View.as_view(), name='purchase_order_update'),
    path('orders/<int:pk>/edit/step1/', views.PurchaseOrderEditStep1View.as_view(), name='purchase_order_edit_step1'),
    path('orders/<int:pk>/edit/step2/', views.PurchaseOrderEditStep2View.as_view(), name='purchase_order_edit_step2'),
    path('orders/<int:pk>/edit/step3/', views.PurchaseOrderEditStep3View.as_view(), name='purchase_order_edit_step3'),
    path('orders/<int:pk>/delete/', views.purchase_order_delete, name='purchase_order_delete'),
    path('orders/<int:pk>/receive/', views.purchase_order_receive, name='purchase_order_receive'),
    
    # Inventory creation
    path('orders/<int:pk>/item/<int:item_id>/create-inventory/', views.create_inventory_items, name='create_inventory_items'),
    path('orders/<int:pk>/inventory-list/', views.purchase_order_inventory_list, name='purchase_order_inventory_list'),
    
    # Supplier URLs
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    
    # Supplier Contact URLs
    path('suppliers/<int:supplier_pk>/contacts/add/', views.supplier_contact_add, name='supplier_contact_add'),
    path('suppliers/<int:supplier_pk>/contacts/<int:contact_pk>/delete/', views.supplier_contact_delete, name='supplier_contact_delete'),
    
    # AJAX endpoints
    path('product/<int:product_id>/info/', views.get_product_info, name='get_product_info'),
]