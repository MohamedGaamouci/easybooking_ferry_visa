from django.contrib.contenttypes.models import ContentType        # <--- Import this
from django.contrib.contenttypes.fields import GenericForeignKey  # <--- Import this
import random
import string
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


def generate_invoice_number():
    return 'INV-' + ''.join(random.choices(string.digits, k=8))


class Invoice(models.Model):
    """
    The Invoice Header.
    Represents the BILL itself, which can contain multiple items.
    """
    STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )

    invoice_number = models.CharField(
        max_length=20, unique=True, default=generate_invoice_number)
    agency = models.ForeignKey(
        'agencies.Agency', on_delete=models.CASCADE, related_name='invoices')

    # We store the TOTAL of all items here for fast access
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='unpaid')
    created_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,  # If user is deleted, keep the invoice history
        null=True,
        blank=True,
        related_name='created_invoices'
    )

    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'finance_invoice'

    def __str__(self):
        return f"{self.invoice_number} - {self.total_amount} DZD"


# ... (Your Invoice class remains the same) ...


class InvoiceItem(models.Model):
    """
    The Invoice Rows.
    Each row links dynamically to ONE specific service (Ferry, Visa, etc.).
    """
    invoice = models.ForeignKey(
        'Invoice',  # String reference allows Invoice to be defined below or above
        on_delete=models.CASCADE,
        related_name='items'
    )

    description = models.CharField(
        max_length=255, help_text="e.g. Ferry Ticket ALG-MRS")
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # =========================================================
    # DYNAMIC SERVICE LINK (Generic Foreign Key)
    # =========================================================

    # A. Which Model? (e.g., "visas.VisaApplication" or "ferries.FerryRequest")
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # B. Which ID? (e.g., ID #45)
    object_id = models.PositiveIntegerField(null=True, blank=True)

    # C. The Actual Object (Usage: item.service_object)
    service_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        db_table = 'finance_invoice_item'

    def __str__(self):
        return f"{self.amount} - {self.description}"
