# accounting/services.py
from decimal import Decimal
from django.db import transaction, IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from accounting.models import PostingRule, JournalEntry, JournalLine, LedgerAccount

# 프로젝트 구조에 맞춘 import (회사/고객 모델이 customer 앱에 있다고 하셨죠)
from customer.models import (
    Customer,
    Organization as Company,
)  # noqa: F401  (타입 힌트/가독용)


def _rule(company, doc_type):
    try:
        return PostingRule.objects.select_related(
            "debit_account", "credit_account", "tax_account"
        ).get(company=company, doc_type=doc_type)
    except PostingRule.DoesNotExist as e:
        raise ValidationError(
            f"PostingRule 누락: company={getattr(company, 'id', company)} doc_type={doc_type}"
        ) from e


def _bank_account(company, code="1010"):
    try:
        return LedgerAccount.objects.get(company=company, code=code)
    except LedgerAccount.DoesNotExist as e:
        raise ValidationError(
            f"LedgerAccount code {code} not found for company={getattr(company,'id',company)}"
        ) from e


def _find_existing_entry(source_obj):
    ct = ContentType.objects.get_for_model(type(source_obj))
    return JournalEntry.objects.filter(
        source_content_type=ct, source_object_id=source_obj.pk
    ).first()


@transaction.atomic
def post_sale(sale):
    """
    Sale을 원장에 전기. 동일 Sale로 여러 번 호출되어도 전표는 1개만 존재하도록 idempotent.
    """
    # 0) 기존 전표가 있으면 그대로 반환(중복 방지)
    existing = _find_existing_entry(sale)
    if existing:
        # 원문서 플래그만 보정
        if hasattr(sale, "posted") and not sale.posted:
            sale.posted = True
            if hasattr(sale, "posted_at"):
                sale.posted_at = timezone.now()
            sale.save(
                update_fields=["posted"]
                + (["posted_at"] if hasattr(sale, "posted_at") else [])
            )
        return existing

    rule = _rule(sale.company, PostingRule.DocType.SALE)

    debit_acc = rule.debit_account
    if getattr(sale, "is_cash", False):
        debit_acc = _bank_account(sale.company, "1010")  # Bank - Checking

    # 금액 읽기
    amt = Decimal(sale.subtotal or 0)
    tax = Decimal(sale.tax or 0)
    total = Decimal(sale.total or (amt + tax))

    # (선택) 합계 검증/보정: 필요 시 주석 해제
    # if amt + tax != total:
    #     raise ValidationError(f"총액 불일치: subtotal({amt}) + tax({tax}) != total({total})")

    # 1) 전표 생성
    je = JournalEntry.objects.create(
        company=sale.company,
        date=sale.date,
        memo=f"Sale #{sale.pk}",
        customer=getattr(
            sale, "customer", None
        ),  # ✅ 고객 연결(je_only_one_party 제약과 충돌 없음)
        posted=True,
        source_content_type=ContentType.objects.get_for_model(type(sale)),
        source_object_id=sale.pk,
    )

    # 2) 분개
    JournalLine.objects.create(
        entry=je, account=debit_acc, debit=total, description="Sale receipt"
    )
    JournalLine.objects.create(
        entry=je, account=rule.credit_account, credit=amt, description="Sales revenue"
    )
    if tax and rule.tax_account:
        JournalLine.objects.create(
            entry=je, account=rule.tax_account, credit=tax, description="Sales tax"
        )

    # 3) 원문서 플래그
    if hasattr(sale, "posted"):
        sale.posted = True
        updates = ["posted"]
        if hasattr(sale, "posted_at"):
            sale.posted_at = timezone.now()
            updates.append("posted_at")
        sale.save(update_fields=updates)

    return je


@transaction.atomic
def post_purchase(purchase):
    """
    Purchase를 원장에 전기. 동일 Purchase로 여러 번 호출되어도 전표는 1개만 존재하도록 idempotent.
    Draft status purchase orders should not be posted.
    """
    # Don't post draft purchase orders
    if hasattr(purchase, 'status') and purchase.status == 'draft':
        raise ValidationError("Cannot post a draft purchase order to general ledger")
    if hasattr(purchase, 'accounting_status') and purchase.accounting_status == 'DRAFT':
        raise ValidationError("Cannot post a purchase order with DRAFT accounting status")
    
    existing = _find_existing_entry(purchase)
    if existing:
        if hasattr(purchase, "posted") and not purchase.posted:
            purchase.posted = True
            if hasattr(purchase, "posted_at"):
                purchase.posted_at = timezone.now()
            purchase.save(
                update_fields=["posted"]
                + (["posted_at"] if hasattr(purchase, "posted_at") else [])
            )
        return existing

    rule = _rule(purchase.company, PostingRule.DocType.PURCHASE)

    credit_acc = rule.credit_account
    if getattr(purchase, "is_cash", False):
        credit_acc = _bank_account(purchase.company, "1010")  # Bank - Checking

    amt = Decimal(purchase.subtotal or 0)
    tax = Decimal(purchase.tax or 0)
    total = Decimal(purchase.total or (amt + tax))

    # 전표 헤더
    je = JournalEntry.objects.create(
        company=purchase.company,
        date=purchase.date,
        memo=f"Purchase #{purchase.pk}",
        supplier=getattr(purchase, "supplier", None),  # ✅ 공급처 연결
        posted=True,
        source_content_type=ContentType.objects.get_for_model(type(purchase)),
        source_object_id=purchase.pk,
    )

    # 분개
    JournalLine.objects.create(
        entry=je,
        account=rule.debit_account,
        debit=amt,
        description="Purchase expense/COGS",
    )
    if tax and rule.tax_account:
        # 매입세금 공제계정을 쓸 거면 rule.tax_account를 별도로 두고 여기에 차변 전기하세요.
        JournalLine.objects.create(
            entry=je, account=rule.debit_account, debit=tax, description="Purchase tax"
        )
    JournalLine.objects.create(
        entry=je, account=credit_acc, credit=total, description="Payment/AP"
    )

    # 원문서 플래그
    if hasattr(purchase, "posted"):
        purchase.posted = True
        updates = ["posted"]
        if hasattr(purchase, "posted_at"):
            purchase.posted_at = timezone.now()
            updates.append("posted_at")
        purchase.save(update_fields=updates)

    return je


@transaction.atomic
def post_incoming_payment(payment):
    """
    고객 수금 Payment를 전기합니다 (idempotent).
    - 기본: Dr Bank(또는 지정 은행) / Cr Accounts Receivable
    - payment.company 또는 payment.sale.company 중 하나가 있어야 함
    - payment.customer 없으면 sale.customer로 대체
    - payment.amount 를 사용 (부분수금 OK)
    """
    # 이미 전표가 있으면 재전기하지 않음
    existing = _find_existing_entry(payment)
    if existing:
        if hasattr(payment, "posted") and not payment.posted:
            payment.posted = True
            updates = ["posted"]
            if hasattr(payment, "posted_at"):
                payment.posted_at = timezone.now()
                updates.append("posted_at")
            payment.save(update_fields=updates)
        return existing

    # 회사/고객 추론
    company = getattr(payment, "company", None) or getattr(
        getattr(payment, "sale", None), "company", None
    )
    if company is None:
        raise ValidationError(
            "Payment.company 또는 Payment.sale.company 가 필요합니다."
        )
    customer = getattr(payment, "customer", None) or getattr(
        getattr(payment, "sale", None), "customer", None
    )

    rule = _rule(company, PostingRule.DocType.PAYMENT_IN)

    # 은행 계정 선택: financial_account가 있으면 그것의 ledger_account 사용, 없으면 규칙의 debit_account 사용
    debit_acc = rule.debit_account
    
    # Check for financial_account first
    financial_account = getattr(payment, "financial_account", None)
    if financial_account:
        if financial_account.ledger_account:
            # Use the linked ledger account from the financial account
            debit_acc = financial_account.ledger_account
        else:
            # Try to find or create a ledger account for this financial account
            # Default to Bank - Checking (1010) or create based on account type
            account_code_map = {
                'checking': '1010',
                'savings': '1020',
                'credit_card': '2100',
                'line_of_credit': '2200',
            }
            base_code = account_code_map.get(financial_account.account_type, '1010')
            
            # Try to find existing account or use default
            try:
                debit_acc = LedgerAccount.objects.get(
                    company=company,
                    code=base_code,
                    is_active=True
                )
            except LedgerAccount.DoesNotExist:
                # Fall back to rule's debit account
                pass
    else:
        # Legacy: check for bank_account_code
        bank_code = getattr(payment, "bank_account_code", None)
        if bank_code:
            debit_acc = _bank_account(company, bank_code)

    amount = Decimal(getattr(payment, "amount", 0) or 0)
    if amount <= 0:
        raise ValidationError("Payment.amount 는 0보다 커야 합니다.")
    date = getattr(payment, "date", None) or timezone.now().date()

    # 전표 생성
    memo = f"Incoming payment #{payment.pk}"
    if financial_account:
        memo += f" - {financial_account.account_name}"
    
    je = JournalEntry.objects.create(
        company=company,
        date=date,
        memo=memo,
        customer=customer,  # ✅ 고객 연결 (제약: customer/supplier 동시 금지)
        posted=True,
        source_content_type=ContentType.objects.get_for_model(type(payment)),
        source_object_id=payment.pk,
    )

    # 분개: Dr Cash/Bank / Cr A/R
    JournalLine.objects.create(
        entry=je, account=debit_acc, debit=amount, description="Customer payment"
    )
    JournalLine.objects.create(
        entry=je, account=rule.credit_account, credit=amount, description="Apply to A/R"
    )

    # 원문서 플래그 업데이트 - Payment uses status field
    if hasattr(payment, "status") and payment.status in ['pending', 'processing']:
        payment.status = 'completed'
        payment.save(update_fields=['status'])

    return je


@transaction.atomic
def rollback_journal_entry(journal_entry):
    """
    Rollback/delete a posted journal entry and update the source document.
    This will delete the journal entry and mark the source document as unposted.
    """
    # Get the source document if it exists
    source_obj = None
    if journal_entry.source_content_type and journal_entry.source_object_id:
        try:
            source_obj = journal_entry.source_content_type.get_object_for_this_type(
                pk=journal_entry.source_object_id
            )
        except ObjectDoesNotExist:
            pass  # Source document no longer exists
    
    # Update the source document to mark it as unposted
    if source_obj:
        # Handle different source document types
        if hasattr(source_obj, 'is_posted'):
            source_obj.is_posted = False
            source_obj.posted_at = None
            source_obj.save(update_fields=['is_posted', 'posted_at'])
        elif hasattr(source_obj, 'posted'):
            source_obj.posted = False
            if hasattr(source_obj, 'posted_at'):
                source_obj.posted_at = None
                source_obj.save(update_fields=['posted', 'posted_at'])
            else:
                source_obj.save(update_fields=['posted'])
        elif hasattr(source_obj, 'status'):
            # For Payment model which uses status field
            if source_obj.status == 'completed':
                source_obj.status = 'pending'
                source_obj.save(update_fields=['status'])
    
    # Store journal entry info for return message
    entry_id = journal_entry.pk
    entry_memo = journal_entry.memo
    
    # Delete the journal entry (this will cascade delete journal lines)
    journal_entry.delete()
    
    return {
        'success': True,
        'message': f'Journal Entry #{entry_id} ({entry_memo}) has been rolled back',
        'source_updated': source_obj is not None
    }


@transaction.atomic
def post_outgoing_payment(vendor_payment):
    """
    공급처 지급 전기 (idempotent).
    - 기본: Dr AP / Cr Bank
    - 선지급(발주만 있고 AP가 없거나, is_advance=True)일 때: Dr Vendor Advances(1310) / Cr Bank
    - 부분지급 OK
    - bank_account_code로 지출 계좌 선택 가능(기본 1010)
    """
    # 이미 전표가 있으면 그대로 반환
    existing = _find_existing_entry(vendor_payment)
    if existing:
        updates = []
        if hasattr(vendor_payment, "posted") and not vendor_payment.posted:
            vendor_payment.posted = True
            updates.append("posted")
        if hasattr(vendor_payment, "posted_at") and not getattr(
            vendor_payment, "posted_at", None
        ):
            vendor_payment.posted_at = timezone.now()
            updates.append("posted_at")
        if updates:
            vendor_payment.save(update_fields=updates)
        return existing

    # 회사/공급처/발주 참조 확보
    po = getattr(vendor_payment, "purchase_order", None)
    company = getattr(vendor_payment, "company", None) or getattr(po, "company", None)
    if company is None:
        raise ValidationError(
            "VendorPayment.company 또는 VendorPayment.purchase_order.company 가 필요합니다."
        )
    supplier = getattr(vendor_payment, "supplier", None) or getattr(
        po, "supplier", None
    )

    # 금액/일자
    amount = Decimal(getattr(vendor_payment, "amount", 0) or 0)
    if amount <= 0:
        raise ValidationError("지급 금액(amount)은 0보다 커야 합니다.")
    date = getattr(vendor_payment, "date", None) or timezone.now().date()
    bank_code = getattr(vendor_payment, "bank_account_code", None)

    # 규칙 및 계정
    rule = _rule(company, PostingRule.DocType.PAYMENT_OUT)  # 기본 Dr AP / Cr Bank
    debit_acc = rule.debit_account  # AP
    credit_acc = rule.credit_account  # Bank
    if bank_code:
        credit_acc = _bank_account(company, bank_code)

    # 선지급 판단: 명시 플래그 또는 AP가 아직 없는 상태(PO만 존재)로 간주
    is_advance = bool(
        getattr(vendor_payment, "is_advance", False)
        or (po is not None and not getattr(po, "has_vendor_bill", False))
    )
    if is_advance:
        # Use a vendor advances account (1310) for prepayments
        try:
            debit_acc = LedgerAccount.objects.get(company=company, code="1310")
        except LedgerAccount.DoesNotExist:
            # Fallback to regular AP account if vendor advances account doesn't exist
            debit_acc = rule.debit_account

    # 전표 생성
    memo_bits = [f"Outgoing payment #{vendor_payment.pk}"]
    if po:
        memo_bits.append(f"PO #{po.pk}")
    memo = " / ".join(memo_bits)

    je = JournalEntry.objects.create(
        company=company,
        date=date,
        memo=memo,
        supplier=supplier,  # ✅ 공급처 연결
        posted=True,
        source_content_type=ContentType.objects.get_for_model(type(vendor_payment)),
        source_object_id=vendor_payment.pk,
    )

    # 분개: Dr (AP 또는 선지급) / Cr Bank
    JournalLine.objects.create(
        entry=je, account=debit_acc, debit=amount, description="Vendor payment"
    )
    JournalLine.objects.create(
        entry=je, account=credit_acc, credit=amount, description="Cash/Bank"
    )

    # 원문서 플래그
    updates = []
    if hasattr(vendor_payment, "posted") and not vendor_payment.posted:
        vendor_payment.posted = True
        updates.append("posted")
    if hasattr(vendor_payment, "posted_at") and not getattr(
        vendor_payment, "posted_at", None
    ):
        vendor_payment.posted_at = timezone.now()
        updates.append("posted_at")
    if updates:
        vendor_payment.save(update_fields=updates)

    return je


def post_expense(expense):
    """
    Post an expense to the general ledger.
    Creates journal entry: DR Expense Account / CR Cash/Bank or Accounts Payable
    """
    from .models import JournalEntry, JournalLine, LedgerAccount, Expense
    from django.contrib.contenttypes.models import ContentType
    from decimal import Decimal
    
    # Check if already posted
    existing = JournalEntry.objects.filter(
        source_content_type=ContentType.objects.get_for_model(Expense),
        source_object_id=expense.pk
    ).first()
    if existing:
        return existing
    
    # Determine expense account (debit side)
    if expense.expense_account:
        debit_account = expense.expense_account
    else:
        # Map category to default expense accounts
        category_account_map = {
            'rent': '5100',  # Rent Expense
            'utilities': '5200',  # Utilities Expense
            'salaries': '5300',  # Salaries Expense
            'insurance': '5400',  # Insurance Expense
            'supplies': '5500',  # Office Supplies Expense
            'marketing': '5600',  # Marketing Expense
            'travel': '5700',  # Travel Expense
            'professional': '5800',  # Professional Services
            'maintenance': '5900',  # Maintenance Expense
            'depreciation': '5950',  # Depreciation Expense
            'taxes': '6000',  # Tax Expense
            'interest': '6100',  # Interest Expense
            'other': '6900',  # Other Expenses
        }
        
        account_code = category_account_map.get(expense.category, '6900')
        
        # Try to find or create the expense account
        try:
            debit_account = LedgerAccount.objects.get(
                company=expense.company,
                code=account_code,
                is_active=True
            )
        except LedgerAccount.DoesNotExist:
            # Create the expense account if it doesn't exist
            category_name = dict(expense.EXPENSE_CATEGORY_CHOICES).get(expense.category, 'Other Expenses')
            debit_account = LedgerAccount.objects.create(
                company=expense.company,
                code=account_code,
                name=category_name,
                type=LedgerAccount.Type.EXPENSE,
                is_active=True
            )
    
    # Determine credit account based on payment status
    if expense.is_paid and expense.financial_account:
        # If paid, credit the financial account (bank/credit card)
        if expense.financial_account.ledger_account:
            credit_account = expense.financial_account.ledger_account
        else:
            # Default to Cash account
            credit_account = LedgerAccount.objects.get_or_create(
                company=expense.company,
                code='1010',
                defaults={'name': 'Bank - Checking', 'type': LedgerAccount.Type.ASSET}
            )[0]
    else:
        # If not paid, credit Accounts Payable
        credit_account = LedgerAccount.objects.get_or_create(
            company=expense.company,
            code='2000',
            defaults={'name': 'Accounts Payable', 'type': LedgerAccount.Type.LIABILITY}
        )[0]
    
    # Create journal entry
    je = JournalEntry.objects.create(
        company=expense.company,
        date=expense.expense_date,
        memo=f"Expense #{expense.expense_number} - {expense.vendor_name} - {expense.description[:50]}",
        supplier=expense.vendor,
        posted=True,
        source_content_type=ContentType.objects.get_for_model(Expense),
        source_object_id=expense.pk,
    )
    
    # Create journal lines
    # Debit expense account for the amount before tax
    JournalLine.objects.create(
        entry=je,
        account=debit_account,
        debit=expense.amount,
        description=f"{dict(expense.EXPENSE_CATEGORY_CHOICES).get(expense.category)} - {expense.vendor_name}"
    )
    
    # If there's tax, debit a tax expense account
    if expense.tax_amount > 0:
        tax_account = LedgerAccount.objects.get_or_create(
            company=expense.company,
            code='5050',
            defaults={'name': 'Sales Tax Expense', 'type': LedgerAccount.Type.EXPENSE}
        )[0]
        JournalLine.objects.create(
            entry=je,
            account=tax_account,
            debit=expense.tax_amount,
            description="Sales tax on expense"
        )
    
    # Credit cash/bank or accounts payable for total amount
    JournalLine.objects.create(
        entry=je,
        account=credit_account,
        credit=expense.total_amount,
        description=f"Payment to {expense.vendor_name}" if expense.is_paid else f"Payable to {expense.vendor_name}"
    )
    
    return je
