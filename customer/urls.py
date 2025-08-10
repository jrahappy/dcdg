from django.urls import path
from . import views

app_name = 'customer'

urlpatterns = [
    # Customer URLs - using function-based views
    path('', views.customer_list, name='customer_list'),
    path('create/', views.customer_create, name='customer_create'),
    path('create/<int:customer_pk>/address/', views.customer_create_step2, name='customer_create_step2'),
    path('<int:pk>/', views.customer_detail, name='customer_detail'),
    path('<int:pk>/edit/', views.customer_update, name='customer_update'),
    path('<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    # Customer Address URLs (for user's own addresses)
    path('addresses/', views.address_list, name='address_list'),
    path('addresses/add/', views.address_create, name='address_create'),
    path('addresses/<int:pk>/edit/', views.address_update, name='address_update'),
    path('addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),
    path('addresses/<int:pk>/set-default/', views.set_default_address, name='set_default_address'),
    
    # Customer-specific Address URLs
    path('<int:customer_pk>/addresses/add/', views.customer_address_create, name='customer_address_create'),
    
    # Customer Contact URLs
    path('<int:customer_pk>/contacts/', views.contact_list, name='contact_list'),
    path('<int:customer_pk>/contacts/add/', views.contact_create, name='contact_create'),
    path('<int:customer_pk>/contacts/<int:pk>/edit/', views.contact_update, name='contact_update'),
    path('<int:customer_pk>/contacts/<int:pk>/delete/', views.contact_delete, name='contact_delete'),
    path('<int:customer_pk>/contacts/<int:pk>/toggle-primary/', views.toggle_contact_primary, name='toggle_contact_primary'),
    
    # Customer Note URLs
    path('<int:customer_pk>/notes/', views.note_list, name='note_list'),
    path('<int:customer_pk>/notes/add/', views.note_create, name='note_create'),
    path('<int:customer_pk>/notes/<int:pk>/delete/', views.note_delete, name='note_delete'),
    
    # Customer Document URLs
    path('<int:customer_pk>/documents/', views.document_list, name='document_list'),
    path('<int:customer_pk>/documents/add/', views.document_create, name='document_create'),
    path('<int:customer_pk>/documents/<int:pk>/delete/', views.document_delete, name='document_delete'),
    
    # Organization Management URLs (Admin only)
    path('my-organization/', views.my_organization, name='my_organization'),
    path('organizations/', views.organization_list, name='organization_list'),
    path('organizations/create/', views.organization_create, name='organization_create'),
    path('organizations/<int:pk>/', views.organization_detail, name='organization_detail'),
    path('organizations/<int:pk>/edit/', views.organization_update, name='organization_update'),
    path('organizations/<int:pk>/delete/', views.organization_delete, name='organization_delete'),
    path('organizations/<int:pk>/add-member/', views.organization_add_member, name='organization_add_member'),
    path('organizations/<int:pk>/remove-member/<int:user_id>/', views.organization_remove_member, name='organization_remove_member'),
]