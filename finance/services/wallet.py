from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .notifications import notify_balance_change
from ..models import Account, Transaction

# =========================================================
# 1. CORE TRANSACTION LOGIC (The Engine)
# =========================================================

from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone


def execute_transaction(
    account_id,
    amount,
    trans_type,
    description,
    user=None,
    related_invoice=None,
    related_topup=None,
    service_obj=None
):
    """
    The Single Source of Truth for moving money.
    Automatically handles signs (+/-) based on trans_type.
    """

    # 1. Ensure amount is a Decimal and get its absolute value
    # We use abs() so the function can decide the sign based on trans_type
    clean_amount = abs(Decimal(str(amount)))

    with transaction.atomic():
        # 2. LOCK THE ROW (Pessimistic Locking)
        try:
            acc_locked = Account.objects.select_for_update().get(id=account_id)
        except Account.DoesNotExist:
            raise ValidationError("Account not found.")

        # 3. DETERMINE THE SIGN (+ or -)
        # Deposits and Refunds INCREASE balance
        if trans_type in ['deposit', 'refund']:
            final_amount = clean_amount

        # Payments DECREASE balance
        elif trans_type == 'payment':
            final_amount = -clean_amount

        # Adjustments keep the sign provided by the user (manual correction)
        elif trans_type == 'adjustment':
            final_amount = Decimal(str(amount))

        else:
            raise ValidationError(f"Invalid transaction type: {trans_type}")

        # 4. CHECK FUNDS (Strict Cash Rule)
        if final_amount < 0:
            if acc_locked.balance + final_amount < 0:
                raise ValidationError(
                    f"Insufficient Funds. Current Balance: {acc_locked.balance} | "
                    f"Attempted Charge: {abs(final_amount)}"
                )

        # 5. UPDATE BALANCE
        acc_locked.balance += final_amount
        acc_locked.updated_at = timezone.now()
        acc_locked.save()

        # 6. CREATE HISTORY RECORD
        new_transaction = Transaction.objects.create(
            account=acc_locked,
            transaction_type=trans_type,
            amount=final_amount,
            balance_after=acc_locked.balance,
            description=description,
            created_by=user,
            invoice=related_invoice,
            top_up=related_topup,
            # Link the Generic Foreign Key if service_obj is passed
            service_object=service_obj
        )

    # === NOTIFY OUTSIDE THE TRANSACTION ===
    # We do this after the with block so we don't hold the DB lock
    # while waiting for an email server.
    try:
        notify_balance_change(
            account=acc_locked,
            amount=final_amount,
            change_type=trans_type,
            reason=description
        )
    except Exception as e:
        # Log error but don't roll back the financial transaction
        import logging
        logger = logging.getLogger(__name__)
        logger.error(
            f"Notification failed for Trans ID {new_transaction.id}: {e}")

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
