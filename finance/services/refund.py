from django.db import transaction
from django.core.exceptions import ValidationError
from ..models import Invoice, Transaction
from .wallet import execute_transaction, get_account


def refund_invoice(invoice_id, user, reason="Cancellation"):
    """
    Safely refunds a specific invoice back to the Agency Wallet.

    Checks:
    1. Invoice exists and is 'paid'.
    2. Has not already been refunded.

    Actions:
    1. Credits wallet (Positive Amount to Balance).
    2. Marks Invoice as 'refunded'.
    3. Links transaction to original invoice for audit.
    """
    with transaction.atomic():
        # 1. Lock & Validate Invoice
        try:
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise ValidationError("Invoice not found.")

        if invoice.status != 'paid':
            raise ValidationError(
                f"Cannot refund. Invoice status is '{invoice.status}'.")

        # 2. Calculate Refund Amount (Positive)
        refund_amount = invoice.total_amount

        # 3. Get Account
        account = get_account(invoice.agency)

        # 4. Execute Refund Transaction (Increases Balance)
        # This puts real cash back into the account.
        execute_transaction(
            account_id=account.id,
            amount=refund_amount,   # Money IN
            trans_type='refund',
            description=f"Refund: {invoice.invoice_number} - {reason}",
            user=user,
            related_invoice=invoice
        )

        # 5. Update Invoice Status
        invoice.status = 'refunded'
        invoice.save()

        return True, "Refund processed successfully."
