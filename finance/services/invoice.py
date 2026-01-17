from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import Invoice, InvoiceItem, Transaction, Account
from .wallet import get_account

# =========================================================
# 1. CREATION LOGIC (GATE 1: CREDIT & RESERVATION)
# =========================================================


def create_invoice(agency, items_data, user=None, due_date=None):
    """
    Creates an UNPAID invoice and RESERVES the amount from the Credit Line.

    Args:
        agency (Agency): The client.
        items_data (list): List of dicts with 'amount', 'description', 'service_object'.
    """
    if not items_data:
        raise ValidationError("Cannot create an empty invoice.")

    # Calculate total cost upfront
    total_cost = sum(item.get('amount', 0) for item in items_data)

    with transaction.atomic():
        # 1. GET & LOCK ACCOUNT
        account = get_account(agency)
        acc_locked = Account.objects.select_for_update().get(id=account.id)

        # 2. GATE 1: CHECK OPERATIONAL VOLUME (Credit Limit)
        # Formula: Available Volume = Credit Limit - Unpaid Hold
        # We ignore 'Balance' here. Purchasing power comes from Credit Limit.
        available_volume = acc_locked.buying_power

        if available_volume < total_cost:
            raise ValidationError(
                f"Credit Limit Reached. "
                f"Available Volume: {available_volume} | Required: {total_cost}"
            )

        # 3. RESERVE THE FUNDS (Increase Hold)
        acc_locked.unpaid_hold += total_cost
        acc_locked.save()

        # 4. CREATE INVOICE RECORD
        invoice = Invoice.objects.create(
            agency=agency,
            status='unpaid',
            created_by=user,
            due_date=due_date,
            total_amount=total_cost
        )

        # 5. CREATE LINE ITEMS
        for item in items_data:
            InvoiceItem.objects.create(
                invoice=invoice,
                description=item.get('description', 'Service Fee'),
                amount=item.get('amount', 0),
                service_object=item.get('service_object')  # Generic Link
            )

        return invoice


def create_single_service_invoice(service_object, amount, description, user):
    """
    Helper to create an invoice for a single service (Visa, Ferry, etc).
    """
    item_data = [{
        'description': description,
        'amount': amount,
        'service_object': service_object
    }]

    return create_invoice(
        agency=service_object.agency,
        items_data=item_data,
        user=user
    )


# =========================================================
# 2. PAYMENT LOGIC (GATE 2: SETTLEMENT)
# =========================================================

def pay_invoice(invoice_id, user=None):
    """
    Settles an Invoice using Real Cash (Balance).

    1. Checks if Agency has enough CASH Balance.
    2. Deducts Cash.
    3. Releases the Credit Hold.
    """
    with transaction.atomic():
        # 1. Lock Invoice
        try:
            invoice = Invoice.objects.select_for_update().get(id=invoice_id)
        except Invoice.DoesNotExist:
            raise ValidationError("Invoice not found.")

        if invoice.status != 'unpaid':
            return False, f"Invoice is {invoice.status}, cannot pay."

        # 2. Lock Account
        account = get_account(invoice.agency)
        acc_locked = Account.objects.select_for_update().get(id=account.id)
        amount = invoice.total_amount

        # 3. GATE 2: CHECK REAL CASH BALANCE
        # The client MUST have enough cash to cover this bill.
        if acc_locked.balance < amount:
            missing = amount - acc_locked.balance
            return False, f"Insufficient Balance. Missing {missing} DZD."

        # 4. EXECUTE SETTLEMENT
        # A. Deduct Real Money
        acc_locked.balance -= amount

        # B. Release the Operational Hold (Restores Credit Limit)
        acc_locked.unpaid_hold -= amount

        acc_locked.save()

        # 5. LOG TRANSACTION (The Ledger)
        Transaction.objects.create(
            account=acc_locked,
            transaction_type='payment',
            amount=-amount,  # Money Leaving
            balance_after=acc_locked.balance,
            description=f"Settlement: Invoice {invoice.invoice_number}",
            created_by=user,
            invoice=invoice
        )

        # 6. UPDATE INVOICE STATUS
        invoice.status = 'paid'
        invoice.paid_at = timezone.now()
        invoice.save()

        return True, "Payment Successful."


# =========================================================
# 3. CANCELLATION LOGIC
# =========================================================

def cancel_invoice(invoice_id, user):
    """
    Cancels an UNPAID invoice and releases the Hold.
    """
    with transaction.atomic():
        invoice = Invoice.objects.select_for_update().get(id=invoice_id)

        if invoice.status != 'unpaid':
            raise ValidationError("Can only cancel unpaid invoices.")

        # Release the Hold so they get their Buying Power back
        account = get_account(invoice.agency)
        acc_locked = Account.objects.select_for_update().get(id=account.id)

        acc_locked.unpaid_hold -= invoice.total_amount
        acc_locked.save()

        invoice.status = 'cancelled'
        invoice.save()

        return True


# =========================================================
# 4. AUTO-SETTLEMENT (SMART LOGIC)
# =========================================================

def auto_settle_invoices(account):
    """
    Called after a Top-Up.
    Loops through unpaid invoices (Oldest First) and pays them
    using the newly available Balance.
    """
    # 1. Get all unpaid invoices, oldest first (FIFO)
    unpaid_invoices = Invoice.objects.filter(
        agency=account.agency,
        status='unpaid'
    ).order_by('created_at')

    results = []

    for invoice in unpaid_invoices:
        # Refresh account data in every loop iteration to get accurate balance
        # (Since we just deducted money in the previous loop)
        account.refresh_from_db()

        # Check strict Gate 2 (Does Balance cover this invoice?)
        if account.balance >= invoice.total_amount:
            # Pay it!
            # We pass None as user since this is a system action
            success, msg = pay_invoice(invoice.id, user=None)
            if success:
                results.append(f"#{invoice.invoice_number}")
        else:
            # If we can't afford the oldest invoice, we stop.
            # This prevents paying new small invoices while leaving old big ones.
            break

    return results
