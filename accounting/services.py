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
    """
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

    # 은행 계정 선택: 규칙의 debit_account를 기본으로, 필요 시 payment.bank_account_code로 덮어쓰기
    debit_acc = rule.debit_account
    bank_code = getattr(payment, "bank_account_code", None)
    if bank_code:
        debit_acc = _bank_account(company, bank_code)

    amount = Decimal(getattr(payment, "amount", 0) or 0)
    if amount <= 0:
        raise ValidationError("Payment.amount 는 0보다 커야 합니다.")
    date = getattr(payment, "date", None) or timezone.now().date()

    # 전표 생성
    je = JournalEntry.objects.create(
        company=company,
        date=date,
        memo=f"Incoming payment #{payment.pk}",
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

    # 원문서 플래그 업데이트
    updates = []
    if hasattr(payment, "posted") and not payment.posted:
        payment.posted = True
        updates.append("posted")
    if hasattr(payment, "posted_at") and not getattr(payment, "posted_at", None):
        payment.posted_at = timezone.now()
        updates.append("posted_at")
    if updates:
        payment.save(update_fields=updates)

    return je


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
        debit_acc = _vendor_advance_account(
            company, code=getattr(vendor_payment, "advance_account_code", "1310")
        )

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
