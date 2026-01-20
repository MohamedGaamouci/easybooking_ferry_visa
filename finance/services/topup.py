from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from ..models import TopUpRequest, Account
from .wallet import execute_transaction

# =========================================================
# 1. AGENT ACTIONS
# =========================================================


def create_topup_request(agency, amount, receipt_image, reference_number=''):
    """
    Creates a pending request for funds.
    """
    if float(amount) <= 0:
        raise ValidationError("Amount must be positive.")

    # Auto-heal account if missing
    try:
        account = agency.account
    except Account.DoesNotExist:
        account = Account.objects.create(agency=agency)

    topup = TopUpRequest.objects.create(
        account=account,
        amount=amount,
        receipt_image=receipt_image,
        reference_number=reference_number,
        status='pending'
    )

    return topup


# =========================================================
# 2. ADMIN ACTIONS
# =========================================================


def approve_topup_request(request_id, admin_user):
    """
    Approves a request and moves money into the wallet.
    """
    with transaction.atomic():
        # 1. Lock Request to prevent double-processing
        try:
            topup = TopUpRequest.objects.select_for_update().get(id=request_id)
        except TopUpRequest.DoesNotExist:
            raise ValidationError("TopUp Request not found.")

        # 2. State Guard: Critical to prevent double deposit
        if topup.status == 'approved':
            raise ValidationError("This request has already been approved.")

        if topup.status != 'pending':
            raise ValidationError(
                f"Cannot approve. Request is currently '{topup.status}'."
            )

        # 3. Add Money (Deposit)
        # execute_transaction ensures the balance increases (+)
        execute_transaction(
            account_id=topup.account.id,
            amount=topup.amount,
            trans_type='deposit',
            description=f"TopUp Approved (Ref: {topup.reference_number})",
            user=admin_user,
            related_topup=topup
        )

        # 4. Finalize TopUp Request
        topup.status = 'approved'
        topup.reviewed_by = admin_user
        topup.reviewed_at = timezone.now()  # Good for audit logs
        topup.save()

        return topup


def reject_topup_request(request_id, admin_user, reason=""):
    """
    Rejects a pending request.
    """
    with transaction.atomic():
        try:
            topup = TopUpRequest.objects.select_for_update().get(id=request_id)
        except TopUpRequest.DoesNotExist:
            raise ValidationError("TopUp Request not found.")

        if topup.status != 'pending':
            raise ValidationError(
                f"Cannot reject. Status is '{topup.status}'.")

        topup.status = 'rejected'
        topup.admin_note = reason
        topup.reviewed_by = admin_user
        topup.save()

        return topup
