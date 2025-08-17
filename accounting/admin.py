from django.contrib import admin
from django.db.models import Sum, Q
from django.utils.html import format_html
from .models import LedgerAccount, JournalEntry, JournalLine, PostingRule, Expense


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 2
    fields = ['account', 'debit', 'credit', 'description']
    autocomplete_fields = ['account']


@admin.register(LedgerAccount)
class LedgerAccountAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'type', 'company', 'is_active', 'get_balance']
    list_filter = ['type', 'is_active', 'company']
    search_fields = ['code', 'name']
    ordering = ['company', 'code']
    
    def get_balance(self, obj):
        """Calculate current balance for the account"""
        lines = JournalLine.objects.filter(
            account=obj,
            entry__posted=True
        )
        total_debit = lines.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = lines.aggregate(Sum('credit'))['credit__sum'] or 0
        
        # For debit accounts (Asset, Expense), balance = debit - credit
        # For credit accounts (Liability, Equity, Revenue), balance = credit - debit
        if obj.type in ['ASSET', 'EXPENSE']:
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit
            
        color = 'green' if balance >= 0 else 'red'
        return format_html(
            '<span style="color: {};">${:,.2f}</span>',
            color, abs(balance)
        )
    get_balance.short_description = 'Balance'


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'date', 'company', 'memo', 'get_customer_supplier', 
                    'posted', 'get_total_amount', 'created_at']
    list_filter = ['posted', 'date', 'company']
    search_fields = ['memo', 'customer__name', 'supplier__name']
    date_hierarchy = 'date'
    readonly_fields = ['source_content_type', 'source_object_id', 'created_at']
    inlines = [JournalLineInline]
    
    def get_customer_supplier(self, obj):
        if obj.customer:
            return f"Customer: {obj.customer}"
        elif obj.supplier:
            return f"Supplier: {obj.supplier}"
        return "-"
    get_customer_supplier.short_description = 'Party'
    
    def get_total_amount(self, obj):
        total = obj.lines.filter(debit__gt=0).aggregate(Sum('debit'))['debit__sum'] or 0
        return format_html('${:,.2f}', total)
    get_total_amount.short_description = 'Amount'
    
    fieldsets = (
        (None, {
            'fields': ('company', 'date', 'memo', 'posted')
        }),
        ('Party Information', {
            'fields': ('customer', 'supplier'),
            'description': 'Only one of customer or supplier can be selected'
        }),
        ('Source Document', {
            'fields': ('source_content_type', 'source_object_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(PostingRule)
class PostingRuleAdmin(admin.ModelAdmin):
    list_display = ['company', 'doc_type', 'debit_account', 'credit_account', 'tax_account']
    list_filter = ['company', 'doc_type']
    autocomplete_fields = ['debit_account', 'credit_account', 'tax_account']
    
    fieldsets = (
        (None, {
            'fields': ('company', 'doc_type')
        }),
        ('Account Mapping', {
            'fields': ('debit_account', 'credit_account', 'tax_account'),
            'description': 'Define which accounts to debit and credit for this document type'
        })
    )


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['expense_number', 'expense_date', 'vendor_name', 'category', 
                    'get_amount_display', 'status', 'is_posted']
    list_filter = ['status', 'category', 'expense_date', 'company']
    search_fields = ['expense_number', 'vendor_name', 'description', 'reference_number']
    date_hierarchy = 'expense_date'
    readonly_fields = ['expense_number', 'created_at', 'updated_at', 'created_by']
    autocomplete_fields = ['vendor', 'expense_account', 'financial_account']
    
    def get_amount_display(self, obj):
        color = 'green' if obj.status == 'posted' else 'black'
        return format_html(
            '<span style="color: {};">${:,.2f}</span>',
            color, obj.total_amount
        )
    get_amount_display.short_description = 'Total Amount'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'expense_number', 'expense_date', 'due_date', 'status')
        }),
        ('Vendor Information', {
            'fields': ('vendor_name', 'vendor', 'reference_number')
        }),
        ('Expense Details', {
            'fields': ('category', 'description', 'amount', 'tax_amount', 'total_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'financial_account', 'paid_date'),
            'classes': ('collapse',)
        }),
        ('Accounting', {
            'fields': ('expense_account',),
            'description': 'Leave blank to use default expense account for the category'
        }),
        ('Attachments & Notes', {
            'fields': ('receipt_file', 'notes'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('created_by', 'approved_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New expense
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['mark_as_approved', 'mark_as_paid', 'post_to_ledger']
    
    def mark_as_approved(self, request, queryset):
        updated = queryset.filter(status='draft').update(
            status='approved',
            approved_by=request.user
        )
        self.message_user(request, f'{updated} expense(s) marked as approved.')
    mark_as_approved.short_description = 'Mark selected expenses as approved'
    
    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='approved').update(
            status='paid',
            paid_date=timezone.now().date()
        )
        self.message_user(request, f'{updated} expense(s) marked as paid.')
    mark_as_paid.short_description = 'Mark selected expenses as paid'
    
    def post_to_ledger(self, request, queryset):
        from accounting.services import post_expense
        posted = 0
        for expense in queryset.filter(status__in=['approved', 'paid']):
            try:
                post_expense(expense)
                expense.status = 'posted'
                expense.save()
                posted += 1
            except Exception as e:
                self.message_user(request, f'Error posting expense {expense.expense_number}: {e}', level='ERROR')
        self.message_user(request, f'{posted} expense(s) posted to ledger.')
    post_to_ledger.short_description = 'Post selected expenses to ledger'
