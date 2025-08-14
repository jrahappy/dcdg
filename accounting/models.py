from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from decimal import Decimal
from sales.models import Invoice, InvoiceItem, Payment
from customer.models import Customer, Organization as Company
from purchases.models import Supplier


class LedgerAccount(models.Model):
    """총계정원장 계정과목 (B안: Account → LedgerAccount)."""

    class Type(models.TextChoices):
        ASSET = "ASSET", "Asset"
        LIABILITY = "LIABILITY", "Liability"
        EQUITY = "EQUITY", "Equity"
        REVENUE = "REVENUE", "Revenue"
        EXPENSE = "EXPENSE", "Expense"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="accounts"
    )
    code = models.CharField(max_length=20)  # 예: 1000, 1100 ...
    name = models.CharField(max_length=120)
    type = models.CharField(max_length=10, choices=Type.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gl_account"  # 명시적 테이블명(가독성↑)
        verbose_name = "Account (GL)"
        verbose_name_plural = "Accounts (GL)"
        unique_together = ("company", "code")
        indexes = [
            models.Index(fields=["company", "type"]),
            models.Index(fields=["company", "code"]),
        ]

    def __str__(self):
        return f"[{self.code}] {self.name}"


# -----------------------------
# 원장(전표/분개)
# -----------------------------


class JournalEntry(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="journal_entries"
    )
    date = models.DateField()
    memo = models.CharField(max_length=255, blank=True)

    # ✅ 거래처 분리: 둘 중 하나만 세팅
    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_entries",
    )
    supplier = models.ForeignKey(
        Supplier,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_entries",
    )

    posted = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # 원천 문서 추적(현행 유지)
    source_content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    source_object_id = models.PositiveIntegerField(null=True, blank=True)
    source_object = GenericForeignKey("source_content_type", "source_object_id")

    class Meta:
        indexes = [
            models.Index(fields=["company", "date"]),
            models.Index(fields=["customer"]),
            models.Index(fields=["supplier"]),
            models.Index(fields=["source_content_type", "source_object_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                name="je_only_one_party",
                check=~(Q(customer__isnull=False) & Q(supplier__isnull=False)),
            ),
        ]

    def __str__(self):
        return f"JE#{self.pk} {self.date} {self.memo or ''}".strip()

    def clean(self):
        debit = sum((line.debit or Decimal("0")) for line in self.lines.all())
        credit = sum((line.credit or Decimal("0")) for line in self.lines.all())
        if debit != credit:
            raise ValidationError(
                f"JournalEntry 불균형: debit({debit}) != credit({credit})"
            )


class JournalLine(models.Model):
    """전표의 분개행(차변 또는 대변 한쪽 금액만)."""

    entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name="lines"
    )
    account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name="journal_lines",
    )
    debit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    credit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [models.Index(fields=["account"]), models.Index(fields=["entry"])]

    def clean(self):
        is_debit = self.debit and self.debit > 0
        is_credit = self.credit and self.credit > 0
        if is_debit and is_credit:
            raise ValidationError("한 분개행은 debit 또는 credit 중 하나만 입력합니다.")
        if not is_debit and not is_credit:
            raise ValidationError("debit 또는 credit 중 하나는 양수여야 합니다.")


# -----------------------------
# 전기 규칙(문서 유형별 계정 매핑)
# -----------------------------
class PostingRule(models.Model):
    class DocType(models.TextChoices):
        SALE = "SALE", "Sale"
        PURCHASE = "PURCHASE", "Purchase"
        PAYMENT_IN = "PAYMENT_IN", "Incoming payment"
        PAYMENT_OUT = "PAYMENT_OUT", "Outgoing payment"
        REFUND = "REFUND", "Refund/Credit note"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="posting_rules"
    )
    doc_type = models.CharField(max_length=20, choices=DocType.choices)

    debit_account = models.ForeignKey(
        LedgerAccount, on_delete=models.PROTECT, related_name="+"
    )
    credit_account = models.ForeignKey(
        LedgerAccount, on_delete=models.PROTECT, related_name="+"
    )
    tax_account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )  # 선택

    class Meta:
        unique_together = ("company", "doc_type")
