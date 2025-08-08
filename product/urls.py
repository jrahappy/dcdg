from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('create/', views.product_create, name='product_create'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('<int:pk>/edit/', views.product_update, name='product_update'),
    path('<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('<int:pk>/duplicate/', views.product_duplicate, name='product_duplicate'),
    path('<int:pk>/quick-update/', views.product_quick_update, name='product_quick_update'),
    path('<int:pk>/upload-image/', views.product_upload_image, name='product_upload_image'),
    path('<int:pk>/upload-document/', views.product_upload_document, name='product_upload_document'),
    path('image/<int:pk>/delete/', views.product_image_delete, name='product_image_delete'),
    
    # Inventory URLs
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/create/', views.inventory_create, name='inventory_create'),
    path('inventory/<int:pk>/', views.inventory_detail, name='inventory_detail'),
    path('inventory/<int:pk>/edit/', views.inventory_update, name='inventory_update'),
    path('inventory/<int:pk>/delete/', views.inventory_delete, name='inventory_delete'),
    
    # Product Option URLs
    path('options/', views.option_list, name='option_list'),
    path('options/create/', views.option_create, name='option_create'),
    path('options/<int:pk>/', views.option_detail, name='option_detail'),
    path('options/<int:pk>/edit/', views.option_update, name='option_update'),
    path('options/<int:pk>/delete/', views.option_delete, name='option_delete'),
    path('options/<int:option_pk>/items/add/', views.option_item_create, name='option_item_create'),
    path('options/items/<int:pk>/delete/', views.option_item_delete, name='option_item_delete'),
    
    # Category URLs
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/', views.category_detail, name='category_detail'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
]