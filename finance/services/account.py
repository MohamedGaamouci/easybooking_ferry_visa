from decimal import Decimal
from django.db.models import Sum, Q
from django.core.exceptions import ValidationError
from ..models import Account, Transaction, Invoice

# =========================================================
# 1. RETRIEVAL & CHECKS (STRICT LOGIC APPLIED HERE)
# =========================================================


def get_account(agency):
    """
    Retrieves the account for an agency.
    Auto-creates it if it's missing (Self-Healing).
    """
    try:
        return agency.account
    except Account.DoesNotExist:
        return Account.objects.create(agency=agency)


def check_solvency(account, amount_needed):
    """
    GATE 1 CHECK: Purchasing Power.
    Used by the Frontend to decide if the booking form is shown.

    Strict Rule: We check Buying Power (Credit Limit - Hold).
    We do NOT check Cash Balance here.
    """
    return account.buying_power >= amount_needed


def get_account_stats(account):
    """
    Aggregates financial data for the Dashboard.
    Shows the user exactly why they might be blocked (Cash vs Volume).
    """
    return {
        # GATE 2: CASH (For paying bills)
        'cash_balance': account.balance,

        # GATE 1: VOLUME (For making bookings)
        'credit_limit': account.credit_limit,
        'reserved_amount': account.unpaid_hold,
        'buying_power': account.buying_power,  # (Limit - Hold)

        # General Stats
        'unpaid_invoices_count': Invoice.objects.filter(agency=account.agency, status='unpaid').count(),
        'total_spent': Transaction.objects.filter(
            account=account,
            transaction_type='payment'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
    }


# =========================================================
# 2. ADMINISTRATIVE UPDATES
# =========================================================

def update_credit_limit(account_id, new_limit, admin_user=None):
    """
    Admin updates the operational volume (Credit Line) for an agency.
    """
    if float(new_limit) < 0:
        raise ValidationError("Credit limit must be a positive number.")

    account = Account.objects.get(id=account_id)
    account.credit_limit = new_limit
    account.save()
    return account


# =========================================================
# 3. REPORTING & SEARCH
# =========================================================

def get_transaction_ledger(account, search_query=None, type_filter=None, start_date=None, end_date=None):
    """
    Retrieves, filters, and searches the transaction history.
    """
    # 1. Base Query
    qs = Transaction.objects.filter(account=account).select_related(
        'created_by',
        'invoice',
        'top_up'
    )

    # 2. Apply Date Filters
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    # 3. Apply Type Filter
    if type_filter and type_filter not in ['all', '', None]:
        qs = qs.filter(transaction_type=type_filter)

    # 4. Apply Smart Search
    if search_query:
        term = search_query.strip()

        q_filter = Q(description__icontains=term)
        # Fix: Ensure we use the correct field name 'invoice_number'
        q_filter |= Q(invoice__invoice_number__icontains=term)
        q_filter |= Q(top_up__reference_number__icontains=term)

        clean_num = term.replace(',', '.')
        if clean_num.replace('.', '', 1).isdigit():
            q_filter |= Q(amount=clean_num)

        qs = qs.filter(q_filter)

    return qs.order_by('-created_at')


def get_statement_export_data(account, start_date=None, end_date=None):
    """
    Prepares data for PDF/Excel. 
    Includes running totals and categorizes In/Out.
    """
    transactions = get_transaction_ledger(
        account, None, None, start_date, end_date)

    total_in = 0
    total_out = 0

    export_rows = []

    for t in transactions:
        if t.amount > 0:
            total_in += t.amount
            credit = t.amount
            debit = 0
        else:
            total_out += abs(t.amount)
            credit = 0
            debit = abs(t.amount)

        # FIX: Handle reference safely and use correct field names
        ref = "-"
        if t.invoice:
            ref = t.invoice.invoice_number  # <--- FIXED (Was .reference)
        elif t.top_up:
            ref = t.top_up.reference_number

        export_rows.append({
            'date': t.created_at.strftime('%Y-%m-%d %H:%M'),
            'reference': ref,
            'description': t.description,
            'credit': credit,
            'debit': debit,
            'balance': t.balance_after,
            'type': t.get_transaction_type_display()
        })

    summary = {
        'agency': account.agency.company_name,
        'period_start': start_date or 'All Time',
        'period_end': end_date or 'Now',
        'total_deposited': total_in,
        'total_spent': total_out,
        'closing_balance': account.balance
    }

    return summary, export_rows
