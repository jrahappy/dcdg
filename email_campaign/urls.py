from django.urls import path
from . import views

app_name = 'email_campaign'

urlpatterns = [
    path('', views.campaign_list, name='campaign_list'),
    path('customer-selection/', views.customer_selection, name='customer_selection'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('target-group-cart/', views.target_group_cart_view, name='target_group_cart'),
    path('clear-cart/', views.clear_cart, name='clear_cart'),
    path('campaign/create/', views.campaign_create, name='campaign_create'),
    path('campaign/create/<int:target_group_id>/', views.campaign_create, name='campaign_create_with_group'),
    path('campaign/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaign/<int:pk>/send/', views.send_campaign, name='send_campaign'),
    path('campaign/<int:pk>/delete/', views.campaign_delete, name='campaign_delete'),
    
    # Target Group URLs
    path('target-groups/', views.target_group_list, name='target_group_list'),
    path('target-groups/<int:pk>/', views.target_group_detail, name='target_group_detail'),
    path('target-groups/<int:pk>/edit/', views.target_group_edit, name='target_group_edit'),
    path('target-groups/<int:pk>/delete/', views.target_group_delete, name='target_group_delete'),
]