from ..models import Invoice
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from ..models import Invoice, InvoiceItem, Transaction, Account
from .wallet import get_account_balance


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
        account = get_account_balance(agency)
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
        try:
            acc_locked = Account.objects.select_for_update().get(agency=invoice.agency)
        except Account.DoesNotExist:
            return False, "Agency Account not found."
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
        account = get_account_balance(invoice.agency)
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


# ... (Previous create/pay/cancel functions) ...

# =========================================================
# 5. SEARCH & FILTER ENGINE
# =========================================================


def search_invoices(agency=None, user=None, search_term=None, status=None, min_amount=None, max_amount=None,
                    service_type=None, created_after=None, created_before=None,
                    paid_after=None, paid_before=None, due_date=None):
    """
    Master Search Method for Invoices.

    Args:
        agency (Agency): Filter by specific agency.
        user (User): Filter by the creator (created_by).
        search_term (str): Searches Invoice Number OR Item Descriptions.
        status (str): 'paid', 'unpaid', 'cancelled', 'refunded'.
        min_amount (decimal): Total amount >= X.
        max_amount (decimal): Total amount <= X.
        service_type (str): Searches for specific service keywords (e.g., 'Visa').
        created_after (date/datetime): Created on or after this date.
        created_before (date/datetime): Created on or before this date.
        paid_after (date/datetime): Paid on or after this date.
        paid_before (date/datetime): Paid on or before this date.
        due_date (date): Exact due date match.
    """

    # 1. Start with all (or agency specific)
    queryset = Invoice.objects.select_related(
        'agency', 'created_by').prefetch_related('items')

    if agency:
        queryset = queryset.filter(agency=agency)

    # 2. User Filter (Creator)
    if user:
        queryset = queryset.filter(created_by=user)

    # 3. Status Filter
    if status:
        queryset = queryset.filter(status=status)

    # 4. Amount Range (Greater/Less Than)
    if min_amount is not None:
        queryset = queryset.filter(total_amount__gte=min_amount)
    if max_amount is not None:
        queryset = queryset.filter(total_amount__lte=max_amount)

    # 5. Dates Logic
    # Created At
    if created_after:
        queryset = queryset.filter(created_at__gte=created_after)
    if created_before:
        queryset = queryset.filter(created_at__lte=created_before)

    # Paid At
    if paid_after:
        queryset = queryset.filter(paid_at__gte=paid_after)
    if paid_before:
        queryset = queryset.filter(paid_at__lte=paid_before)

    # Due Date (Exact)
    if due_date:
        queryset = queryset.filter(due_date=due_date)

    # 6. Service Type (Contextual Search)
    # Checks if any item inside the invoice matches the description
    if service_type:
        queryset = queryset.filter(
            items__description__icontains=service_type).distinct()

    # 7. General Text Search (Smart Search)
    # Searches Invoice Number OR inside the Items (e.g., searching "Turkey" finds Visa Turkey invoices)
    if search_term:
        queryset = queryset.filter(
            Q(invoice_number__icontains=search_term) |
            Q(items__description__icontains=search_term)
        ).distinct()

    return queryset.order_by('-created_at')
