from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Q, F, DecimalField, Value, Case, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse
from decimal import Decimal
from datetime import datetime, timedelta
import calendar

from .models import LedgerAccount, JournalEntry, JournalLine, PostingRule, Expense
from .services import post_sale, post_purchase, post_incoming_payment, post_outgoing_payment, rollback_journal_entry, post_expense
from sales.models import Invoice, Payment
from purchases.models import PurchaseOrder
from customer.models import Organization as Company


@staff_member_required
def accounting_dashboard(request):
    """Main accounting dashboard with key metrics"""
    # Get company (assuming single company for now, adjust as needed)
    company = Company.objects.first()
    if not company:
        messages.error(request, "No company found. Please create a company first.")
        return redirect('admin:index')
    
    # Date range for current month
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    end_of_month = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    
    # Get key account balances
    def get_account_balance(account_code):
        try:
            account = LedgerAccount.objects.get(company=company, code=account_code)
            lines = JournalLine.objects.filter(account=account, entry__posted=True)
            total_debit = lines.aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
            total_credit = lines.aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
            
            if account.type in ['ASSET', 'EXPENSE']:
                return total_debit - total_credit
            else:
                return total_credit - total_debit
        except LedgerAccount.DoesNotExist:
            return Decimal('0')
    
    # Calculate key metrics
    cash_balance = get_account_balance('1010')  # Bank account
    accounts_receivable = get_account_balance('1100')  # A/R (corrected from 1200)
    accounts_payable = get_account_balance('2000')  # A/P
    
    # Revenue and expenses for current month
    revenue_accounts = LedgerAccount.objects.filter(company=company, type='REVENUE')
    expense_accounts = LedgerAccount.objects.filter(company=company, type='EXPENSE')
    
    month_revenue = JournalLine.objects.filter(
        account__in=revenue_accounts,
        entry__posted=True,
        entry__date__gte=start_of_month,
        entry__date__lte=end_of_month
    ).aggregate(
        total=Coalesce(Sum('credit'), Decimal('0')) - Coalesce(Sum('debit'), Decimal('0'))
    )['total'] or Decimal('0')
    
    month_expenses = JournalLine.objects.filter(
        account__in=expense_accounts,
        entry__posted=True,
        entry__date__gte=start_of_month,
        entry__date__lte=end_of_month
    ).aggregate(
        total=Coalesce(Sum('debit'), Decimal('0')) - Coalesce(Sum('credit'), Decimal('0'))
    )['total'] or Decimal('0')
    
    # Recent journal entries
    recent_entries = JournalEntry.objects.filter(
        company=company
    ).select_related('customer', 'supplier').order_by('-date', '-id')[:10]
    
    # Unposted documents count
    unposted_invoices = Invoice.objects.filter(
        Q(is_posted__isnull=True) | Q(is_posted=False)
    ).count()
    
    unposted_purchases = PurchaseOrder.objects.filter(
        Q(is_posted__isnull=True) | Q(is_posted=False)
    ).count()
    
    # Payment model doesn't have a posted field, so we'll count all pending payments
    unposted_payments = Payment.objects.filter(
        status__in=['pending', 'processing']
    ).count()
    
    context = {
        'company': company,
        'cash_balance': cash_balance,
        'accounts_receivable': accounts_receivable,
        'accounts_payable': accounts_payable,
        'month_revenue': month_revenue,
        'month_expenses': month_expenses,
        'net_income': month_revenue - month_expenses,
        'recent_entries': recent_entries,
        'unposted_invoices': unposted_invoices,
        'unposted_purchases': unposted_purchases,
        'unposted_payments': unposted_payments,
        'current_month': today.strftime('%B %Y'),
    }
    
    return render(request, 'accounting/dashboard.html', context)


@staff_member_required
def chart_of_accounts(request):
    """Display chart of accounts with balances"""
    company = Company.objects.first()
    if not company:
        messages.error(request, "No company found.")
        return redirect('accounting:dashboard')
    
    # Get all accounts with calculated balances
    accounts = LedgerAccount.objects.filter(
        company=company
    ).order_by('type', 'code')
    
    # Calculate balance for each account
    accounts_with_balance = []
    for account in accounts:
        lines = JournalLine.objects.filter(account=account, entry__posted=True)
        total_debit = lines.aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
        total_credit = lines.aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
        
        if account.type in ['ASSET', 'EXPENSE']:
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit
        
        accounts_with_balance.append({
            'account': account,
            'debit': total_debit,
            'credit': total_credit,
            'balance': balance
        })
    
    # Group by type
    grouped_accounts = {}
    for item in accounts_with_balance:
        account_type = item['account'].get_type_display()
        if account_type not in grouped_accounts:
            grouped_accounts[account_type] = []
        grouped_accounts[account_type].append(item)
    
    context = {
        'company': company,
        'grouped_accounts': grouped_accounts,
    }
    
    return render(request, 'accounting/chart_of_accounts.html', context)


@staff_member_required
def general_ledger(request):
    """General ledger view with filtering"""
    company = Company.objects.first()
    if not company:
        messages.error(request, "No company found.")
        return redirect('accounting:dashboard')
    
    # Handle bulk approval
    if request.method == 'POST':
        action = request.POST.get('bulk_action')
        entry_ids = request.POST.getlist('entry_ids')
        
        if action == 'approve' and entry_ids:
            approved_count = 0
            for entry_id in entry_ids:
                try:
                    entry = JournalEntry.objects.get(pk=entry_id, company=company)
                    if not entry.posted:
                        # Check if balanced
                        lines = entry.lines.all()
                        total_debit = sum(line.debit for line in lines if line.debit)
                        total_credit = sum(line.credit for line in lines if line.credit)
                        
                        if total_debit == total_credit:
                            entry.posted = True
                            entry.save()
                            approved_count += 1
                except JournalEntry.DoesNotExist:
                    pass
            
            if approved_count > 0:
                messages.success(request, f"Successfully approved {approved_count} journal entries.")
            else:
                messages.warning(request, "No entries were approved. Entries may already be posted or unbalanced.")
        
        return redirect('accounting:general_ledger')
    
    # Get filter parameters
    account_id = request.GET.get('account')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    status_filter = request.GET.get('status', 'all')  # all, posted, draft
    
    # Base query
    entries = JournalEntry.objects.filter(
        company=company
    ).select_related('customer', 'supplier').prefetch_related('lines__account')
    
    # Apply status filter
    if status_filter == 'posted':
        entries = entries.filter(posted=True)
    elif status_filter == 'draft':
        entries = entries.filter(posted=False)
    
    # Apply filters
    if date_from:
        entries = entries.filter(date__gte=date_from)
    if date_to:
        entries = entries.filter(date__lte=date_to)
    if account_id:
        entries = entries.filter(lines__account_id=account_id).distinct()
    
    entries = entries.order_by('-date', '-id')
    
    # Add totals to each entry
    entries_with_totals = []
    for entry in entries:
        lines = entry.lines.all()
        total_debit = sum(line.debit for line in lines if line.debit)
        total_credit = sum(line.credit for line in lines if line.credit)
        entry.total_debit = total_debit
        entry.total_credit = total_credit
        entries_with_totals.append(entry)
    
    # Pagination
    paginator = Paginator(entries_with_totals, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get accounts for filter dropdown
    accounts = LedgerAccount.objects.filter(
        company=company,
        is_active=True
    ).order_by('code')
    
    context = {
        'company': company,
        'page_obj': page_obj,
        'accounts': accounts,
        'selected_account': account_id,
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
    }
    
    return render(request, 'accounting/general_ledger.html', context)


@staff_member_required
def journal_entry_detail(request, pk):
    """View details of a journal entry"""
    entry = get_object_or_404(JournalEntry, pk=pk)
    
    # Handle POST request for approve/unapprove
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            # Check if entry is balanced before approving
            lines = entry.lines.all()
            total_debit = lines.aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
            total_credit = lines.aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
            
            if total_debit != total_credit:
                messages.error(request, f"Cannot approve unbalanced entry. Debit: ${total_debit}, Credit: ${total_credit}")
            else:
                entry.posted = True
                entry.save()
                messages.success(request, f"Journal Entry #{entry.id} has been approved and posted.")
        
        elif action == 'unapprove':
            entry.posted = False
            entry.save()
            messages.warning(request, f"Journal Entry #{entry.id} has been unapproved and unposted.")
        
        return redirect('accounting:journal_entry_detail', pk=pk)
    
    # Get journal lines with account details
    lines = entry.lines.select_related('account').order_by('id')
    
    # Calculate totals
    total_debit = lines.aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
    total_credit = lines.aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
    
    # Build source document URL if available
    source_document_url = None
    if entry.source_content_type and entry.source_object_id:
        model_name = entry.source_content_type.model
        
        # Map model names to their detail URL patterns
        if model_name == 'invoice':
            source_document_url = reverse('sales:invoice_detail', args=[entry.source_object_id])
        elif model_name == 'purchaseorder':
            source_document_url = reverse('purchases:purchase_order_detail', args=[entry.source_object_id])
        elif model_name == 'payment':
            # Payment is usually viewed through invoice detail
            try:
                from sales.models import Payment
                payment = Payment.objects.get(pk=entry.source_object_id)
                if payment.invoice:
                    source_document_url = reverse('sales:invoice_detail', args=[payment.invoice.pk])
            except:
                pass
        elif model_name == 'supplierpayment':
            # Supplier payment is viewed through purchase order detail
            try:
                from purchases.models import SupplierPayment
                payment = SupplierPayment.objects.get(pk=entry.source_object_id)
                if payment.purchase_order:
                    source_document_url = reverse('purchases:purchase_order_detail', args=[payment.purchase_order.pk])
            except:
                pass
    
    context = {
        'entry': entry,
        'lines': lines,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'is_balanced': total_debit == total_credit,
        'source_document_url': source_document_url,
    }
    
    return render(request, 'accounting/journal_entry_detail.html', context)


@staff_member_required
def trial_balance(request):
    """Trial balance report"""
    company = Company.objects.first()
    if not company:
        messages.error(request, "No company found.")
        return redirect('accounting:dashboard')
    
    # Get date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Get all active accounts
    accounts = LedgerAccount.objects.filter(
        company=company,
        is_active=True
    ).order_by('code')
    
    # Calculate balances
    trial_balance_data = []
    total_debit = Decimal('0')
    total_credit = Decimal('0')
    
    for account in accounts:
        # Base query for journal lines
        lines_query = JournalLine.objects.filter(
            account=account,
            entry__posted=True
        )
        
        # Apply date filters
        if date_from:
            lines_query = lines_query.filter(entry__date__gte=date_from)
        if date_to:
            lines_query = lines_query.filter(entry__date__lte=date_to)
        
        # Calculate totals
        account_debit = lines_query.aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
        account_credit = lines_query.aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
        
        # Skip accounts with no activity
        if account_debit == 0 and account_credit == 0:
            continue
        
        # Determine debit or credit balance based on account type
        if account.type in ['ASSET', 'EXPENSE']:
            debit_balance = account_debit - account_credit
            credit_balance = Decimal('0') if debit_balance >= 0 else abs(debit_balance)
            debit_balance = max(debit_balance, Decimal('0'))
        else:
            credit_balance = account_credit - account_debit
            debit_balance = Decimal('0') if credit_balance >= 0 else abs(credit_balance)
            credit_balance = max(credit_balance, Decimal('0'))
        
        trial_balance_data.append({
            'account': account,
            'debit': debit_balance,
            'credit': credit_balance
        })
        
        total_debit += debit_balance
        total_credit += credit_balance
    
    context = {
        'company': company,
        'trial_balance_data': trial_balance_data,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'is_balanced': total_debit == total_credit,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'accounting/trial_balance.html', context)


@staff_member_required
def income_statement(request):
    """Income statement (P&L) report"""
    company = Company.objects.first()
    if not company:
        messages.error(request, "No company found.")
        return redirect('accounting:dashboard')
    
    # Get date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Default to current month if no dates provided
    if not date_from:
        today = timezone.now().date()
        date_from = today.replace(day=1).strftime('%Y-%m-%d')
    if not date_to:
        today = timezone.now().date()
        date_to = today.strftime('%Y-%m-%d')
    
    # Revenue accounts
    revenue_accounts = LedgerAccount.objects.filter(
        company=company,
        type='REVENUE',
        is_active=True
    ).order_by('code')
    
    revenue_data = []
    total_revenue = Decimal('0')
    
    for account in revenue_accounts:
        lines = JournalLine.objects.filter(
            account=account,
            entry__posted=True,
            entry__date__gte=date_from,
            entry__date__lte=date_to
        )
        amount = lines.aggregate(
            total=Coalesce(Sum('credit'), Decimal('0')) - Coalesce(Sum('debit'), Decimal('0'))
        )['total']
        
        if amount != 0:
            revenue_data.append({'account': account, 'amount': amount})
            total_revenue += amount
    
    # Expense accounts
    expense_accounts = LedgerAccount.objects.filter(
        company=company,
        type='EXPENSE',
        is_active=True
    ).order_by('code')
    
    expense_data = []
    total_expenses = Decimal('0')
    
    for account in expense_accounts:
        lines = JournalLine.objects.filter(
            account=account,
            entry__posted=True,
            entry__date__gte=date_from,
            entry__date__lte=date_to
        )
        amount = lines.aggregate(
            total=Coalesce(Sum('debit'), Decimal('0')) - Coalesce(Sum('credit'), Decimal('0'))
        )['total']
        
        if amount != 0:
            expense_data.append({'account': account, 'amount': amount})
            total_expenses += amount
    
    net_income = total_revenue - total_expenses
    
    context = {
        'company': company,
        'revenue_data': revenue_data,
        'expense_data': expense_data,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_income': net_income,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'accounting/income_statement.html', context)


@staff_member_required
def balance_sheet(request):
    """Balance sheet report"""
    company = Company.objects.first()
    if not company:
        messages.error(request, "No company found.")
        return redirect('accounting:dashboard')
    
    # Get as-of date
    as_of_date = request.GET.get('as_of_date', timezone.now().date().strftime('%Y-%m-%d'))
    
    def get_accounts_balance(account_type):
        accounts = LedgerAccount.objects.filter(
            company=company,
            type=account_type,
            is_active=True
        ).order_by('code')
        
        data = []
        total = Decimal('0')
        
        for account in accounts:
            lines = JournalLine.objects.filter(
                account=account,
                entry__posted=True,
                entry__date__lte=as_of_date
            )
            
            debit_total = lines.aggregate(Sum('debit'))['debit__sum'] or Decimal('0')
            credit_total = lines.aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
            
            if account_type in ['ASSET', 'EXPENSE']:
                balance = debit_total - credit_total
            else:
                balance = credit_total - debit_total
            
            if balance != 0:
                data.append({'account': account, 'balance': balance})
                total += balance
        
        return data, total
    
    # Get balances by type
    assets_data, total_assets = get_accounts_balance('ASSET')
    liabilities_data, total_liabilities = get_accounts_balance('LIABILITY')
    equity_data, total_equity_accounts = get_accounts_balance('EQUITY')
    
    # Calculate retained earnings (sum of all revenue - expenses up to date)
    revenue_lines = JournalLine.objects.filter(
        account__company=company,
        account__type='REVENUE',
        entry__posted=True,
        entry__date__lte=as_of_date
    )
    revenue_total = revenue_lines.aggregate(
        total=Coalesce(Sum('credit'), Decimal('0')) - Coalesce(Sum('debit'), Decimal('0'))
    )['total']
    
    expense_lines = JournalLine.objects.filter(
        account__company=company,
        account__type='EXPENSE',
        entry__posted=True,
        entry__date__lte=as_of_date
    )
    expense_total = expense_lines.aggregate(
        total=Coalesce(Sum('debit'), Decimal('0')) - Coalesce(Sum('credit'), Decimal('0'))
    )['total']
    
    retained_earnings = revenue_total - expense_total
    total_equity = total_equity_accounts + retained_earnings
    
    context = {
        'company': company,
        'assets_data': assets_data,
        'liabilities_data': liabilities_data,
        'equity_data': equity_data,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'retained_earnings': retained_earnings,
        'total_liabilities_equity': total_liabilities + total_equity,
        'as_of_date': as_of_date,
        'is_balanced': abs(total_assets - (total_liabilities + total_equity)) < Decimal('0.01'),
    }
    
    return render(request, 'accounting/balance_sheet.html', context)


@staff_member_required
def post_documents(request):
    """Post unposted documents to the general ledger"""
    if request.method == 'POST':
        company = Company.objects.first()
        if not company:
            messages.error(request, "No company found.")
            return redirect('accounting:dashboard')
        
        posted_count = {
            'invoices': 0,
            'purchases': 0,
            'payments': 0
        }
        
        # Post unposted invoices
        unposted_invoices = Invoice.objects.filter(
            Q(is_posted__isnull=True) | Q(is_posted=False)
        )
        for invoice in unposted_invoices:
            try:
                # Add company to invoice if not present
                if not hasattr(invoice, 'company'):
                    invoice.company = company
                invoice.subtotal = invoice.subtotal
                invoice.tax = invoice.tax_amount
                invoice.total = invoice.total_amount
                invoice.date = invoice.invoice_date
                post_sale(invoice)
                invoice.is_posted = True
                invoice.posted_at = timezone.now()
                invoice.save(update_fields=['is_posted', 'posted_at'])
                posted_count['invoices'] += 1
            except Exception as e:
                messages.error(request, f"Error posting invoice {invoice.pk}: {str(e)}")
        
        # Post unposted purchase orders (only approved ones, not drafts)
        unposted_purchases = PurchaseOrder.objects.filter(
            Q(is_posted__isnull=True) | Q(is_posted=False)
        ).exclude(
            status='draft'  # Exclude draft purchase orders from posting
        ).exclude(
            accounting_status='DRAFT'  # Also exclude accounting draft status
        )
        for purchase in unposted_purchases:
            try:
                if not hasattr(purchase, 'company'):
                    purchase.company = company
                purchase.subtotal = purchase.subtotal
                purchase.tax = purchase.tax_amount
                purchase.total = purchase.total_amount
                purchase.date = purchase.order_date
                post_purchase(purchase)
                purchase.is_posted = True
                purchase.posted_at = timezone.now()
                purchase.save(update_fields=['is_posted', 'posted_at'])
                posted_count['purchases'] += 1
            except Exception as e:
                messages.error(request, f"Error posting purchase order {purchase.pk}: {str(e)}")
        
        # Post unposted payments (using status field instead of posted)
        unposted_payments = Payment.objects.filter(
            status__in=['pending', 'processing']
        )
        for payment in unposted_payments:
            try:
                if not hasattr(payment, 'company'):
                    payment.company = company
                payment.date = payment.payment_date
                payment.sale = payment.invoice  # Map invoice to sale
                post_incoming_payment(payment)
                # Mark payment as completed instead of using posted field
                payment.status = 'completed'
                payment.save(update_fields=['status'])
                posted_count['payments'] += 1
            except Exception as e:
                messages.error(request, f"Error posting payment {payment.pk}: {str(e)}")
        
        # Success message
        total_posted = sum(posted_count.values())
        if total_posted > 0:
            messages.success(
                request,
                f"Successfully posted {posted_count['invoices']} invoices, "
                f"{posted_count['purchases']} purchase orders, and "
                f"{posted_count['payments']} payments."
            )
        else:
            messages.info(request, "No unposted documents found.")
        
        return redirect('accounting:dashboard')
    
    # GET request - show confirmation page
    unposted_invoices = Invoice.objects.filter(
        Q(is_posted__isnull=True) | Q(is_posted=False)
    )
    unposted_purchases = PurchaseOrder.objects.filter(
        Q(is_posted__isnull=True) | Q(is_posted=False)
    )
    # Payment model doesn't have a posted field, use status instead
    unposted_payments = Payment.objects.filter(
        status__in=['pending', 'processing']
    )
    
    context = {
        'unposted_invoices': unposted_invoices,
        'unposted_purchases': unposted_purchases,
        'unposted_payments': unposted_payments,
    }
    
    return render(request, 'accounting/post_documents.html', context)


@login_required
@staff_member_required
def delete_journal_entry(request, pk):
    """Delete/rollback a journal entry and update the source document"""
    journal_entry = get_object_or_404(JournalEntry, pk=pk)
    
    if request.method == 'POST':
        try:
            result = rollback_journal_entry(journal_entry)
            messages.success(request, result['message'])
            if result['source_updated']:
                messages.info(request, 'Source document has been marked as unposted.')
        except Exception as e:
            messages.error(request, f'Error rolling back journal entry: {str(e)}')
        
        # Redirect to general ledger or referring page
        next_url = request.POST.get('next', reverse('accounting:general_ledger'))
        return redirect(next_url)
    
    # GET request - show confirmation page
    context = {
        'journal_entry': journal_entry,
        'next': request.GET.get('next', reverse('accounting:general_ledger'))
    }
    return render(request, 'accounting/confirm_delete_journal.html', context)


@staff_member_required
def expense_list(request):
    """List all expenses with filtering and pagination"""
    company = Company.objects.first()
    if not company:
        messages.error(request, "No company found.")
        return redirect('accounting:dashboard')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    category = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')
    
    # Build queryset
    expenses = Expense.objects.filter(company=company)
    
    if status:
        expenses = expenses.filter(status=status)
    if category:
        expenses = expenses.filter(category=category)
    if date_from:
        expenses = expenses.filter(expense_date__gte=date_from)
    if date_to:
        expenses = expenses.filter(expense_date__lte=date_to)
    if search:
        expenses = expenses.filter(
            Q(expense_number__icontains=search) |
            Q(vendor_name__icontains=search) |
            Q(description__icontains=search) |
            Q(reference_number__icontains=search)
        )
    
    # Calculate totals
    total_amount = expenses.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    
    # Pagination
    paginator = Paginator(expenses, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'company': company,
        'page_obj': page_obj,
        'expenses': page_obj,
        'total_amount': total_amount,
        'status_choices': Expense.STATUS_CHOICES,
        'category_choices': Expense.EXPENSE_CATEGORY_CHOICES,
        'filters': {
            'status': status,
            'category': category,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    }
    
    return render(request, 'accounting/expense_list.html', context)


@staff_member_required
def expense_create(request):
    """Create a new expense"""
    company = Company.objects.first()
    if not company:
        messages.error(request, "No company found.")
        return redirect('accounting:dashboard')
    
    if request.method == 'POST':
        from .forms import ExpenseForm
        form = ExpenseForm(request.POST, request.FILES, company=company)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.company = company
            expense.created_by = request.user
            expense.save()
            
            # If status is posted, post to journal
            if expense.status == 'posted':
                try:
                    from .services import post_expense
                    je = post_expense(expense)
                    messages.success(request, f'Expense {expense.expense_number} created and posted to journal entry #{je.id}')
                except Exception as e:
                    messages.warning(request, f'Expense created but could not be posted: {str(e)}')
            else:
                messages.success(request, f'Expense {expense.expense_number} created successfully')
            
            return redirect('accounting:expense_list')
    else:
        from .forms import ExpenseForm
        form = ExpenseForm(company=company)
    
    context = {
        'form': form,
        'company': company,
        'page_title': 'Add Expense',
        'submit_text': 'Create Expense',
    }
    return render(request, 'accounting/expense_form.html', context)


@staff_member_required
def expense_update(request, pk):
    """Update an existing expense"""
    expense = get_object_or_404(Expense, pk=pk)
    company = expense.company
    
    if request.method == 'POST':
        from .forms import ExpenseForm
        form = ExpenseForm(request.POST, request.FILES, instance=expense, company=company)
        if form.is_valid():
            old_status = expense.status
            expense = form.save()
            
            # If status changed to posted, post to journal
            if old_status != 'posted' and expense.status == 'posted':
                try:
                    from .services import post_expense
                    je = post_expense(expense)
                    messages.success(request, f'Expense {expense.expense_number} updated and posted to journal entry #{je.id}')
                except Exception as e:
                    messages.warning(request, f'Expense updated but could not be posted: {str(e)}')
            else:
                messages.success(request, f'Expense {expense.expense_number} updated successfully')
            
            return redirect('accounting:expense_list')
    else:
        from .forms import ExpenseForm
        form = ExpenseForm(instance=expense, company=company)
    
    context = {
        'form': form,
        'expense': expense,
        'company': company,
        'page_title': f'Edit Expense {expense.expense_number}',
        'submit_text': 'Update Expense',
    }
    return render(request, 'accounting/expense_form.html', context)


@staff_member_required
def expense_delete(request, pk):
    """Delete an expense"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        expense_number = expense.expense_number
        
        # Check if expense has been posted
        if expense.is_posted:
            messages.error(request, f'Cannot delete expense {expense_number} as it has been posted to the ledger. Please unpost it first.')
            return redirect('accounting:expense_list')
        
        expense.delete()
        messages.success(request, f'Expense {expense_number} deleted successfully')
        return redirect('accounting:expense_list')
    
    context = {
        'expense': expense,
    }
    return render(request, 'accounting/expense_confirm_delete.html', context)


@staff_member_required  
def expense_post(request, pk):
    """Post an expense to the general ledger"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if expense.is_posted:
        messages.warning(request, f'Expense {expense.expense_number} has already been posted')
    else:
        try:
            from .services import post_expense
            je = post_expense(expense)
            expense.status = 'posted'
            expense.save()
            messages.success(request, f'Expense {expense.expense_number} posted to journal entry #{je.id}')
        except Exception as e:
            messages.error(request, f'Error posting expense: {str(e)}')
    
    return redirect('accounting:expense_list')
