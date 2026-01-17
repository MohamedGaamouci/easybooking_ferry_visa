from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from ..models import Account, Transaction

# =========================================================
# 1. CORE TRANSACTION LOGIC (The Engine)
# =========================================================


def execute_transaction(
    account_id,
    amount,
    trans_type,
    description,
    user=None,
    related_invoice=None,
    related_topup=None
):
    """
    The Single Source of Truth for moving money.
    - Locks the account row (thread-safety).
    - Checks for sufficient funds (if spending).
    - Updates the balance.
    - Creates the Audit Log (Transaction record).

    Args:
        account_id (int): The ID of the wallet/account.
        amount (Decimal): Positive for Deposits, Negative for Payments.
        trans_type (str): 'deposit', 'payment', 'refund', or 'adjustment'.
        description (str): Human readable note.
        user (User): The admin or agent performing the action.
        related_invoice (Invoice): Optional link.
        related_topup (TopUpRequest): Optional link.

    Returns:
        Transaction: The created transaction object.
    """

    # START ATOMIC BLOCK
    # (Either everything succeeds, or nothing changes)
    with transaction.atomic():

        # 1. LOCK THE ROW
        # select_for_update() ensures no one else can modify this specific
        # account until this function finishes. Prevents "Race Conditions".
        try:
            acc_locked = Account.objects.select_for_update().get(id=account_id)
        except Account.DoesNotExist:
            raise ValidationError("Account not found.")

        # 2. CHECK FUNDS (Only for money leaving the account)
        if amount < 0:
            # Calculate what the balance would be
            future_balance = acc_locked.balance + amount

            # Check against Credit Limit
            # Example: Balance 0, Limit 50000. Available = 50000.
            # Spend -60000 -> Future -60000. Limit is -50000. FAIL.
            limit_threshold = -acc_locked.credit_limit

            if future_balance < limit_threshold:
                raise ValidationError(
                    f"Insufficient funds. Transaction declined. "
                    f"Available Limit: {acc_locked.balance + acc_locked.credit_limit} DZD"
                )

        # 3. UPDATE BALANCE
        acc_locked.balance += amount
        acc_locked.updated_at = timezone.now()
        acc_locked.save()

        # 4. CREATE HISTORY RECORD
        new_transaction = Transaction.objects.create(
            account=acc_locked,
            transaction_type=trans_type,
            amount=amount,
            balance_after=acc_locked.balance,
            description=description,
            created_by=user,
            invoice=related_invoice,
            top_up=related_topup
        )

        return new_transaction


# =========================================================
# 2. HELPER SERVICES (Getters & Checks)
# =========================================================

def get_account_balance(agency):
    """
    Quickly get the balance for an Agency object.
    Creates an account if one doesn't exist (Safety net).
    """
    if hasattr(agency, 'account'):
        return agency.account.balance
    else:
        # Auto-heal: Create account if missing
        acc = Account.objects.create(agency=agency)
        return acc.balance


def check_solvency(account, amount_needed):
    """
    Returns True if the account can afford 'amount_needed'.
    amount_needed should be a positive number (cost).
    """
    purchasing_power = account.balance + account.credit_limit
    return purchasing_power >= amount_needed


def get_transaction_history(account_id, limit=50):
    """
    Get recent movements for a specific wallet.
    """
    return Transaction.objects.filter(account_id=account_id).order_by('-created_at')[:limit]
