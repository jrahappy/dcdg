from django.urls import path
from . import views

app_name = 'accounting'

urlpatterns = [
    # Dashboard
    path('', views.accounting_dashboard, name='dashboard'),
    
    # Reports
    path('chart-of-accounts/', views.chart_of_accounts, name='chart_of_accounts'),
    path('general-ledger/', views.general_ledger, name='general_ledger'),
    path('journal-entry/<int:pk>/', views.journal_entry_detail, name='journal_entry_detail'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('income-statement/', views.income_statement, name='income_statement'),
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
    
    # Actions
    path('post-documents/', views.post_documents, name='post_documents'),
    path('journal-entry/<int:pk>/delete/', views.delete_journal_entry, name='delete_journal_entry'),
    
    # Expense URLs
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_update, name='expense_update'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    path('expenses/<int:pk>/post/', views.expense_post, name='expense_post'),
]