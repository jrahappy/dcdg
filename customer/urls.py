from django.urls import path
from . import views

app_name = 'customer'

urlpatterns = [
    # Customer URLs
    path('', views.CustomerListView.as_view(), name='customer_list'),
    path('create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('create/<int:customer_pk>/address/', views.CustomerCreateStep2View.as_view(), name='customer_create_step2'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    
    # Customer Address URLs (for user's own addresses)
    path('addresses/', views.AddressListView.as_view(), name='address_list'),
    path('addresses/add/', views.AddressCreateView.as_view(), name='address_create'),
    path('addresses/<int:pk>/edit/', views.AddressUpdateView.as_view(), name='address_update'),
    path('addresses/<int:pk>/delete/', views.AddressDeleteView.as_view(), name='address_delete'),
    path('addresses/<int:pk>/set-default/', views.set_default_address, name='set_default_address'),
    
    # Customer-specific Address URLs
    path('<int:customer_pk>/addresses/add/', views.CustomerAddressCreateView.as_view(), name='customer_address_create'),
    
    # Customer Contact URLs
    path('<int:customer_pk>/contacts/', views.ContactListView.as_view(), name='contact_list'),
    path('<int:customer_pk>/contacts/add/', views.ContactCreateView.as_view(), name='contact_create'),
    path('<int:customer_pk>/contacts/<int:pk>/edit/', views.ContactUpdateView.as_view(), name='contact_update'),
    path('<int:customer_pk>/contacts/<int:pk>/delete/', views.ContactDeleteView.as_view(), name='contact_delete'),
    path('<int:customer_pk>/contacts/<int:pk>/toggle-primary/', views.toggle_contact_primary, name='toggle_contact_primary'),
    
    # Customer Note URLs
    path('<int:customer_pk>/notes/', views.NoteListView.as_view(), name='note_list'),
    path('<int:customer_pk>/notes/add/', views.NoteCreateView.as_view(), name='note_create'),
    path('<int:customer_pk>/notes/<int:pk>/delete/', views.NoteDeleteView.as_view(), name='note_delete'),
    
    # Customer Document URLs
    path('<int:customer_pk>/documents/', views.DocumentListView.as_view(), name='document_list'),
    path('<int:customer_pk>/documents/add/', views.DocumentCreateView.as_view(), name='document_create'),
    path('<int:customer_pk>/documents/<int:pk>/delete/', views.DocumentDeleteView.as_view(), name='document_delete'),
    
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