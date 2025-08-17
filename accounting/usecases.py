# accounting/usecases.py
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from accounting.models import JournalEntry
from accounting.services import post_sale, post_incoming_payment, post_outgoing_payment  # 이미 만드신 전기 함수 사용


def _find_existing_entry(obj):
    ct = ContentType.objects.get_for_model(type(obj))
    return JournalEntry.objects.filter(
        source_content_type=ct, source_object_id=obj.pk
    ).first()


@transaction.atomic
def approve_and_post_sale(sale):
    """
    1) Sale을 승인 상태로 전환
    2) 이미 전표가 있으면 그대로 반환(중복 전기 방지)
    3) 없으면 post_sale(sale) 호출해 전기
    """
    # 승인 상태로 만들기
    if hasattr(sale, "status"):
        SaleStatus = getattr(sale, "Status", None)
        if SaleStatus and sale.status != SaleStatus.APPROVED:
            sale.status = SaleStatus.APPROVED

    # 기존 전표 있으면 재전기하지 않음
    existing = _find_existing_entry(sale)
    if existing:
        if hasattr(sale, "posted") and not sale.posted:
            sale.posted = True
        if hasattr(sale, "posted_at") and not getattr(sale, "posted_at", None):
            sale.posted_at = timezone.now()
        sale.save(
            update_fields=[
                f for f in ["status", "posted", "posted_at"] if hasattr(sale, f)
            ]
        )
        return existing

    # 신규 전기
    je = post_sale(sale)

    if hasattr(sale, "posted"):
        sale.posted = True
    if hasattr(sale, "posted_at"):
        sale.posted_at = timezone.now()
    sale.save(
        update_fields=[f for f in ["status", "posted", "posted_at"] if hasattr(sale, f)]
    )

    return je


@transaction.atomic
def approve_and_post_incoming_payment(payment):
    """
    1) Payment 승인 상태 전환(있다면)
    2) 전표가 있으면 그대로 반환
    3) 없으면 post_incoming_payment(payment)
    """
    if hasattr(payment, "status"):
        Status = getattr(payment, "Status", None)
        if Status and payment.status != Status.APPROVED:
            payment.status = Status.APPROVED

    existing = _find_existing_entry(payment)
    if existing:
        updates = []
        if hasattr(payment, "posted") and not payment.posted:
            payment.posted = True
            updates.append("posted")
        if hasattr(payment, "posted_at") and not getattr(payment, "posted_at", None):
            payment.posted_at = timezone.now()
            updates.append("posted_at")
        if updates:
            payment.save(
                update_fields=(
                    ["status"] + updates if hasattr(payment, "status") else updates
                )
            )
        return existing

    je = post_incoming_payment(payment)

    updates = []
    if hasattr(payment, "posted"):
        payment.posted = True
        updates.append("posted")
    if hasattr(payment, "posted_at"):
        payment.posted_at = timezone.now()
        updates.append("posted_at")
    if hasattr(payment, "status"):
        updates = ["status"] + updates
    if updates:
        payment.save(update_fields=updates)

    return je


@transaction.atomic
def approve_and_post_outgoing_payment(vendor_payment):
    """
    1) (있다면) 승인 상태로 전환
    2) 기존 전표가 있으면 그대로 반환
    3) 없으면 post_outgoing_payment() 수행
    """
    if hasattr(vendor_payment, "status"):
        Status = getattr(vendor_payment, "Status", None)
        if Status and vendor_payment.status != Status.APPROVED:
            vendor_payment.status = Status.APPROVED

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
            vendor_payment.save(
                update_fields=(["status"] if hasattr(vendor_payment, "status") else [])
                + updates
            )
        return existing

    je = post_outgoing_payment(vendor_payment)

    updates = []
    if hasattr(vendor_payment, "posted"):
        vendor_payment.posted = True
        updates.append("posted")
    if hasattr(vendor_payment, "posted_at"):
        vendor_payment.posted_at = timezone.now()
        updates.append("posted_at")
    if hasattr(vendor_payment, "status"):
        vendor_payment.status = getattr(vendor_payment, "Status").APPROVED
        updates.insert(0, "status")
    if updates:
        vendor_payment.save(update_fields=updates)

    return je
