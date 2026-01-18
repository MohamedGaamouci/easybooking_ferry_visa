# <--- Make sure you import this
from django.forms import ValidationError
from finance.services.invoice import bulk_pay_invoices
from django.template.loader import get_template
from finance.services.invoice import pay_invoice
from django.http import HttpResponse
from xhtml2pdf import pisa  # type: ignore
from django.template.loader import render_to_string
from finance.services.invoice import search_invoices, cancel_invoice, refund_invoice
from finance.services.invoice import search_invoices, cancel_invoice
from django.shortcuts import render
from finance.services.invoice import cancel_invoice
from finance.models import Invoice
from decimal import Decimal
from decimal import Decimal
from django.db import transaction
import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_date

from agencies.models import Agency
from finance.models import Account, Transaction, TopUpRequest
from finance.services.account import get_account
from finance.services.wallet import execute_transaction

# Check if user is Admin/Staff


def is_admin(user):
    if getattr(user, 'agency'):
        return False
    else:
        print(f"{user} is admin ----------")
        return True


@login_required
@user_passes_test(is_admin)
def admin_accounting_dashboard(request):
    """
    Main View: Loads the initial HTML + Stats + Pending Requests.
    """
    total_balance = Account.objects.aggregate(s=Sum('balance'))['s'] or 0
    total_debt = Account.objects.aggregate(s=Sum('unpaid_hold'))['s'] or 0
    pending_total = TopUpRequest.objects.filter(
        status='pending').aggregate(s=Sum('amount'))['s'] or 0

    pending_topups = TopUpRequest.objects.filter(status='pending').select_related(
        'account__agency').order_by('-created_at')
    agencies = Agency.objects.select_related(
        'account').all().order_by('-account__balance')

    context = {
        'total_balance': total_balance,
        'total_debt': total_debt,
        'pending_total': pending_total,
        'pending_topups': pending_topups,
        'agencies': agencies,
    }
    return render(request, 'admin/accounting.html', context)

# =========================================================
# API: LEDGER (SEARCH & PAGINATION)
# =========================================================


@login_required
@user_passes_test(is_admin)
def admin_ledger_api(request):
    query = request.GET.get('q', '')
    trx_type = request.GET.get('type', '')
    page_num = request.GET.get('page', 1)

    qs = Transaction.objects.select_related(
        'account__agency', 'created_by').all().order_by('-created_at')

    if query:
        qs = qs.filter(
            Q(description__icontains=query) |
            Q(account__agency__company_name__icontains=query) |
            Q(amount__icontains=query)
        )
    if trx_type:
        qs = qs.filter(transaction_type=trx_type)

    paginator = Paginator(qs, 15)
    page = paginator.get_page(page_num)

    data = []
    for t in page:
        agency_name = t.account.agency.company_name if t.account else "System"
        data.append({
            'id': t.id,
            'date': t.created_at.strftime("%b %d, %H:%M"),
            'agency': agency_name,
            'description': t.description,
            'amount': float(t.amount),
            'balance_after': float(t.balance_after),
            'type': t.transaction_type
        })

    return JsonResponse({
        'status': 'success',
        'transactions': data,
        'pagination': {
            'current': page.number,
            'total': paginator.num_pages,
            'has_next': page.has_next(),
            'has_prev': page.has_previous()
        }
    })

# =========================================================
# API: ACTIONS (TOP-UP & MANUAL)
# =========================================================


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_process_topup(request, topup_id):
    """Approves or Rejects a Top-Up Request."""
    data = json.loads(request.body)
    action = data.get('action')

    try:
        # Wrap the entire operation in a transaction
        with transaction.atomic():
            top_up = get_object_or_404(
                TopUpRequest, id=topup_id, status='pending')

            if action == 'approve':
                # 1. Move the Money (Wallet Engine)
                # This already uses atomic, but now it acts as a savepoint within this parent transaction
                execute_transaction(
                    account_id=top_up.account.id,
                    amount=top_up.amount,
                    trans_type='deposit',
                    description=f"TopUp Approved: {top_up.reference_number}",
                    user=request.user,
                    related_topup=top_up
                )

                # 2. Update the Request Status
                # If this line fails, the money movement above will roll back!
                top_up.status = 'approved'
                top_up.save()
                msg = "Top-Up Approved."

            elif action == 'reject':
                top_up.status = 'rejected'
                top_up.save()
                msg = "Top-Up Rejected."

        # Fetch stats AFTER the transaction is successfully committed
        new_pending = TopUpRequest.objects.filter(
            status='pending').aggregate(s=Sum('amount'))['s'] or 0
        new_balance = Account.objects.aggregate(s=Sum('balance'))['s'] or 0

        return JsonResponse({
            'status': 'success',
            'msg': msg,
            'stats': {'pending': new_pending, 'balance': new_balance}
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)


# ... other imports ...


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_manual_trx(request):
    """Processes a Manual Credit or Debit using Wallet Engine."""
    data = json.loads(request.body)
    agency_id = data.get('agency_id')

    # 2. FIX: Convert to string first, then to Decimal (Avoids float precision errors)
    try:
        amount_val = data.get('amount', 0)
        amount_raw = Decimal(str(amount_val))
    except (ValueError, TypeError):
        return JsonResponse({'status': 'error', 'msg': 'Invalid Amount format'}, status=400)

    trx_type = data.get('type')  # 'credit' or 'debit'
    reason = data.get('reason')

    try:
        with transaction.atomic():
            agency = Agency.objects.get(id=agency_id)
            account = get_account(agency)

            # Determine signed amount
            final_amount = amount_raw if trx_type == 'credit' else -amount_raw

            # USE YOUR EXISTING ENGINE
            execute_transaction(
                account_id=account.id,
                amount=final_amount,
                trans_type='deposit' if trx_type == 'credit' else 'adjustment',
                description=f"Manual: {reason}",
                user=request.user
            )

        new_balance = Account.objects.aggregate(s=Sum('balance'))['s'] or 0

        return JsonResponse({
            'status': 'success',
            'msg': 'Transaction Processed.',
            'stats': {'balance': new_balance}
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_update_limit(request):
    """
    AJAX: Updates the Credit Limit for an Agency.
    """
    import json
    data = json.loads(request.body)
    agency_id = data.get('agency_id')

    try:
        # 1. Validate Amount
        new_limit = float(data.get('limit', 0))
        if new_limit < 0:
            return JsonResponse({'status': 'error', 'msg': 'Limit cannot be negative.'}, status=400)

        # 2. Update Account
        with transaction.atomic():
            agency = Agency.objects.get(id=agency_id)
            # Use get_account to ensure it exists
            account = get_account(agency)

            old_limit = account.credit_limit
            account.credit_limit = new_limit
            account.save()

            # Optional: Log this change in the ledger as a note?
            # Usually not a transaction, but good to have an audit log if you have one.

        return JsonResponse({
            'status': 'success',
            'msg': f"Limit updated from {old_limit} to {new_limit}"
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)

# finance/views_admin.py


@login_required
@user_passes_test(is_admin)
def admin_agency_api(request):
    """
    API to fetch paginated list of agencies with their financial stats.
    """
    query = request.GET.get('q', '')
    page_num = request.GET.get('page', 1)

    # Base Query
    qs = Agency.objects.select_related(
        'account').all().order_by('-account__balance')

    # Search
    if query:
        qs = qs.filter(
            Q(company_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    # Pagination (10 per page)
    paginator = Paginator(qs, 10)
    page = paginator.get_page(page_num)

    data = []
    for agency in page:
        # Handle account auto-creation if missing (safety)
        try:
            acc = agency.account
            bal = acc.balance
            hold = acc.unpaid_hold
            limit = acc.credit_limit
            power = acc.buying_power
        except:
            bal = 0
            hold = 0
            limit = 0
            power = 0

        data.append({
            'id': agency.id,
            'name': agency.company_name,
            'balance': float(bal),
            'unpaid_hold': float(hold),
            'credit_limit': float(limit),
            'buying_power': float(power),
            'is_solvent': power > 0
        })

    return JsonResponse({
        'status': 'success',
        'agencies': data,
        'pagination': {
            'current': page.number,
            'total': paginator.num_pages,
            'has_next': page.has_next(),
            'has_prev': page.has_previous()
        }
    })


# finance/views_admin.py

@login_required
@user_passes_test(is_admin)
def admin_topups_api(request):
    """
    API to fetch paginated Pending Top-Up Requests.
    """
    page_num = request.GET.get('page', 1)

    # 1. Get Pending Requests
    qs = TopUpRequest.objects.filter(status='pending').select_related(
        'account__agency').order_by('created_at')

    # 2. Paginate (5 per page is usually good for tasks)
    paginator = Paginator(qs, 5)
    page = paginator.get_page(page_num)

    # 3. Serialize
    data = []
    for t in page:
        data.append({
            'id': t.id,
            'created_at': t.created_at.strftime("%b %d, %H:%M"),
            'agency_name': t.account.agency.company_name,
            'reference': t.reference_number,
            'amount': float(t.amount),
            'receipt_url': t.receipt_image.url if t.receipt_image else None
        })

    return JsonResponse({
        'status': 'success',
        'topups': data,
        'pagination': {
            'current': page.number,
            'total': paginator.num_pages,
            'has_next': page.has_next(),
            'has_prev': page.has_previous()
        }
    })


# =========================================================
# API: INVOICES (USING YOUR SERVICE ENGINE)
# =========================================================


@login_required
@user_passes_test(is_admin)
def admin_invoices_api(request):
    """
    API with Full Filtering Capabilities including Agency Name search.
    """
    # 1. Extract Params
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    agency_id = request.GET.get('agency_id')

    amount_min = request.GET.get('amount_min')
    amount_max = request.GET.get('amount_max')

    # Validation: Ensure they are not empty strings before passing
    amount_min = amount_min if amount_min and amount_min.strip() else None
    amount_max = amount_max if amount_max and amount_max.strip() else None

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    page_num = request.GET.get('page', 1)

    # 2. Prepare Date Objects
    d_after = parse_date(date_from) if date_from else None
    d_before = parse_date(date_to) if date_to else None

    target_agency = None
    if agency_id:
        target_agency = Agency.objects.get(id=agency_id)

    # 3. Call Service (WITHOUT search_term)
    # We pass 'None' for search_term so we can handle the complex OR logic here.
    qs = search_invoices(
        search_term=None,  # <--- Important: We handle text search below
        agency=target_agency,
        status=status if status else None,
        min_amount=amount_min if amount_min else None,
        max_amount=amount_max if amount_max else None,
        created_after=d_after,
        created_before=d_before
    )

    # 4. Apply Text Search (Agency OR Invoice # OR Description)
    if query:
        qs = qs.filter(
            Q(invoice_number__icontains=query) |
            Q(items__description__icontains=query) |
            Q(agency__company_name__icontains=query) |  # <--- Added Agency Name
            # <--- Added Email for convenience
            Q(agency__manager__email__icontains=query)
        ).distinct()

    # 5. Pagination
    paginator = Paginator(qs, 15)
    page = paginator.get_page(page_num)

    data = []
    for inv in page:
        data.append({
            'id': inv.id,
            'number': inv.invoice_number,
            'date': inv.created_at.strftime("%Y-%m-%d %H:%M"),
            'agency': inv.agency.company_name,
            'amount': float(inv.total_amount),
            'status': inv.status,
            'due_date': inv.due_date.strftime("%Y-%m-%d") if inv.due_date else "-",
            'is_cancellable': inv.status == 'unpaid',
            'is_refundable': inv.status == 'paid'
        })

    return JsonResponse({
        'status': 'success',
        'invoices': data,
        'pagination': {
            'current': page.number,
            'total': paginator.num_pages,
            'has_next': page.has_next(),
            'has_prev': page.has_previous()
        }
    })


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_invoice_cancel(request, invoice_id):
    """
    Admin Action: Force Cancel an Invoice using the service logic.
    """
    try:
        # USE YOUR EXISTING SERVICE
        # This handles the transaction, locking, and hold release automatically.
        success = cancel_invoice(invoice_id, user=request.user)

        if success:
            return JsonResponse({'status': 'success', 'msg': 'Invoice Cancelled & Hold Released.'})
        else:
            return JsonResponse({'status': 'error', 'msg': 'Could not cancel invoice.'}, status=400)

    except Exception as e:
        # Catches ValidationErrors (like "Can only cancel unpaid invoices")
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_invoice_refund(request, invoice_id):
    """
    Refunds a Paid Invoice.
    """
    try:
        refund_invoice(invoice_id, user=request.user,
                       reason="Admin Dashboard Request")
        return JsonResponse({'status': 'success', 'msg': 'Invoice Refunded. Money returned to wallet.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)


# finance/views_admin.py

@login_required
@user_passes_test(is_admin)
def admin_invoice_detail_api(request, invoice_id):
    """
    Fetches details + line items for a specific invoice.
    """
    try:
        inv = Invoice.objects.select_related(
            'agency').prefetch_related('items').get(id=invoice_id)

        # Build Item List
        items_data = []
        for item in inv.items.all():
            items_data.append({
                'description': item.description,
                'amount': float(item.amount)
            })

        data = {
            'id': inv.id,
            'number': inv.invoice_number,
            'status': inv.status,
            'created_at': inv.created_at.strftime("%b %d, %Y"),
            'due_date': inv.due_date.strftime("%b %d, %Y") if inv.due_date else "N/A",
            'total': float(inv.total_amount),
            'items': items_data,
            # We will build this view later
            'download_url': f"/finance/invoices/{inv.id}/pdf/",
            'can_refund': inv.status == 'paid',
            'can_cancel': inv.status == 'unpaid'
        }
        return JsonResponse({'status': 'success', 'invoice': data})

    except Invoice.DoesNotExist:
        return JsonResponse({'status': 'error', 'msg': 'Invoice not found'}, status=404)


# finance/views_admin.py


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_invoice_pay(request, invoice_id):
    """
    Admin Action: Manually trigger payment using Agency's Wallet.
    """
    try:
        # Calls your existing service which checks Balance > Amount
        success, msg = pay_invoice(invoice_id, user=request.user)

        if success:
            return JsonResponse({'status': 'success', 'msg': msg})
        else:
            # Returns error like "Insufficient Balance"
            return JsonResponse({'status': 'error', 'msg': msg}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
def admin_invoice_pdf(request, invoice_id):
    """
    Generates a PDF for the specific invoice.
    """
    # 1. Fetch Data
    invoice = get_object_or_404(Invoice, id=invoice_id)

    # 2. Prepare Context (Variables used in your HTML)
    context = {
        'invoice': invoice,
        'agency': invoice.agency,
        'items': invoice.items.all(),
        'date': invoice.created_at,
        'user': request.user,  # Info about who printed it
    }

    # 3. Load Your Template
    # Make sure this path matches exactly where your file is inside /templates/
    template_path = 'client/pdf/invoice.html'
    template = get_template(template_path)
    html = template.render(context)

    # 4. Create Response Object
    response = HttpResponse(content_type='application/pdf')
    # 'attachment' forces download. Change to 'inline' to view in browser.
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # 5. Generate PDF
    pisa_status = pisa.CreatePDF(
        html, dest=response
    )

    # 6. Error Handling
    if pisa_status.err:
        return HttpResponse(f'We had some errors <pre>{html}</pre>')

    return response

# simple agency retrieval method for drop down menu


@login_required
@user_passes_test(is_admin)
def admin_agencies_simple_api(request):
    """Returns a lightweight list of agencies with their CURRENT BALANCE."""

    # 1. Query: Fetch ID, Company Name, and Account Balance
    # We access the related account model using 'account__balance'
    agencies_qs = Agency.objects.filter(status='active').values(
        'id', 'company_name', 'account__balance'
    ).order_by('company_name')

    # 2. Formatting: Clean up the data
    data = []
    for ag in agencies_qs:
        data.append({
            'id': ag['id'],
            # PRESERVE OLD KEY (Safety): Keeps 'company_name' so old JS doesn't break
            'company_name': ag['company_name'],

            # ADD NEW KEYS (Feature): Adds 'name' and 'balance' for the Bulk Pay Modal
            'name': ag['company_name'],
            # Converts None to 0.0
            'balance': float(ag['account__balance'] or 0)
        })

    return JsonResponse({'status': 'success', 'agencies': data})


# 4. ADD NEW VIEW: Bulk Pay Action
# finance/views_admin.py


@login_required
@user_passes_test(is_admin)
@require_POST
def admin_bulk_pay(request):
    """
    Receives a list of Invoice IDs and pays them using the atomic service.
    """
    import json
    try:
        data = json.loads(request.body)
        invoice_ids = data.get('invoice_ids', [])

        # Call the Service
        success, msg = bulk_pay_invoices(invoice_ids, user=request.user)

        return JsonResponse({
            'status': 'success',
            'results': {'success': len(invoice_ids), 'msg': msg}
        })

    except ValidationError as e:
        # Expected Logic Errors (Insufficient Funds, Mixed Agencies)
        return JsonResponse({'status': 'error', 'msg': str(e.message)}, status=400)

    except Exception as e:
        # Unexpected System Errors
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)
