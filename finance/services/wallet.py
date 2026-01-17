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

    STRICT MODE UPDATE:
    - Deposits (Positive): Always allowed.
    - Payments (Negative): Only allowed if Balance stays >= 0.
    - Credit Limits are IGNORED here (they are handled in Invoice Creation).
    """

    with transaction.atomic():
        # 1. LOCK THE ROW
        try:
            acc_locked = Account.objects.select_for_update().get(id=account_id)
        except Account.DoesNotExist:
            raise ValidationError("Account not found.")

        # 2. CHECK FUNDS (Strict Cash Rule)
        # If money is leaving, we must have enough REAL CASH.
        if amount < 0:
            if acc_locked.balance + amount < 0:
                raise ValidationError(
                    f"Insufficient Cash Funds. "
                    f"Balance: {acc_locked.balance} | Required: {abs(amount)}"
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
# 2. HELPER SERVICES
# =========================================================

def get_account_balance(agency):
    """
    Quickly get the balance. Auto-heals if account is missing.
    """
    if hasattr(agency, 'account'):
        return agency.account.balance
    else:
        acc = Account.objects.create(agency=agency)
        return acc.balance


def get_transaction_history(account_id, limit=50):
    return Transaction.objects.filter(account_id=account_id).order_by('-created_at')[:limit]
