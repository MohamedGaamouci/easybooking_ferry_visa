from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Invoice, Transaction
from .wallet import execute_transaction, get_account


def refund_invoice(invoice_id, user, reason="Cancellation"):
    """
    Safely refunds a specific invoice back to the Agency Wallet.
    """
    with transaction.atomic():
        # 1. Lock & Validate Invoice
        try:
            # select_for_update prevents two people from refunding at the same time
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise ValidationError("Invoice not found.")

        # CRITICAL: Check status to prevent Double Refund
        if invoice.status == 'refunded':
            raise ValidationError("This invoice has already been refunded.")

        if invoice.status != 'paid':
            raise ValidationError(
                f"Cannot refund. Only 'paid' invoices can be refunded (Status: {invoice.status})."
            )

        # 2. Get Account
        # Ensure your get_account function or logic is robust
        account = invoice.agency.account

        # 3. Execute Refund Transaction
        # We use our helper. Because trans_type is 'refund',
        # it will treat the amount as POSITIVE (Money IN).
        execute_transaction(
            account_id=account.id,
            amount=invoice.total_amount,
            trans_type='refund',
            description=f"Refund: {invoice.invoice_number} - {reason}",
            user=user,
            related_invoice=invoice
        )

        # 4. UPDATE INVOICE STATUS
        invoice.status = 'refunded'
        # Optional: store who performed the refund and when
        invoice.description = f"{invoice.description} | Refunded by {user} for: {reason}"
        invoice.save()

        return True, "Refund processed successfully."
