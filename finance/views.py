from .services.invoice import pay_invoice
from xhtml2pdf import pisa
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import Invoice, InvoiceItem  # Ensure InvoiceItem is imported
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError

# Services
from .services.account import get_account, get_account_stats, get_transaction_ledger
from .services.topup import create_topup_request
from .models import TopUpRequest


from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.dateparse import parse_date

# Import Services
from .services.account import get_account, get_account_stats, get_transaction_ledger
from .services.invoice import search_invoices  # <--- The new engine
from .models import TopUpRequest

# ------------------------------------------------------------
# -------------------- Client Side ---------------------------
# ------------------------------------------------------------


@login_required
def finance_dashboard(request):
    try:
        agency = request.user.managed_agency
        account = get_account(agency)
    except AttributeError:
        return render(request, 'client/error.html', {'msg': 'No agency assigned.'})

    # =========================================================
    # 1. EXTRACT FILTERS
    # =========================================================
    # Common text search (applies to both Invoices and Transactions)
    query = request.GET.get('q', '')

    # Advanced Invoice Filters
    status = request.GET.get('status')            # 'paid', 'unpaid', etc.
# FIX: Check if string is empty, otherwise None
    min_amt = request.GET.get('min_amount')
    if min_amt == '':
        min_amt = None

    max_amt = request.GET.get('max_amount')
    if max_amt == '':
        max_amt = None
    date_from = request.GET.get('date_from')      # Created After
    date_to = request.GET.get('date_to')          # Created Before
    service = request.GET.get('service_type')     # e.g. "Visa"

    # =========================================================
    # 2. GET DATA (Using Services)
    # =========================================================

    # A. Search Invoices (The Power Engine)
    invoices = search_invoices(
        agency=agency,
        search_term=query,
        status=status,
        min_amount=min_amt,
        max_amount=max_amt,
        created_after=parse_date(date_from) if date_from else None,
        created_before=parse_date(date_to) if date_to else None,
        service_type=service
    )

    # B. Search Transactions
    # (We keep this simple for now, mostly filtering by the text query)
    transactions = get_transaction_ledger(
        account=account,
        search_query=query
    )

    # =========================================================
    # 3. AJAX RESPONSE (JSON)
    # =========================================================
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':

        # Serialize Invoices
        invoices_data = []
        for inv in invoices:
            invoices_data.append({
                'id': inv.id,
                'number': inv.invoice_number,
                'date': inv.created_at.strftime("%b %d, %Y"),
                'amount': intcomma(inv.total_amount),
                'status': inv.status,
                'status_display': inv.get_status_display()
            })

        # Serialize Transactions
        transactions_data = []
        for t in transactions:
            # Smart Reference display
            ref = "-"
            if t.invoice:
                ref = f"Ref: #{t.invoice.invoice_number}"
            elif t.top_up:
                ref = f"Ref: #{t.top_up.reference_number or 'CASH'}"

            transactions_data.append({
                'date': t.created_at.strftime("%b %d, %Y"),
                'time': t.created_at.strftime("%H:%M"),
                'description': t.description,
                'ref': ref,
                'type': t.transaction_type,
                'amount': intcomma(t.amount),
                'amount_is_positive': t.amount > 0,
                'balance_after': intcomma(t.balance_after)
            })

        return JsonResponse({
            'status': 'success',
            'invoices': invoices_data,
            'transactions': transactions_data
        })

    # =========================================================
    # 4. STANDARD PAGE LOAD (HTML)
    # =========================================================
    stats = get_account_stats(account)
    pending_topups = TopUpRequest.objects.filter(
        account=account,
        status='pending'
    ).order_by('-created_at')

    context = {
        'account': account,
        'stats': stats,
        'transactions': transactions[:20],  # Limit initial load for speed
        'pending_topups': pending_topups,
        'invoices': invoices[:20],         # Limit initial load for speed
    }
    return render(request, 'client/accounting.html', context)


@login_required
@require_POST
def submit_topup_ajax(request):
    """
    AJAX Endpoint for Top-Up Form submission.
    """
    try:
        agency = request.user.managed_agency

        amount = request.POST.get('amount')
        reference = request.POST.get('reference', '')
        receipt = request.FILES.get('receipt_image')

        if not amount:
            return JsonResponse({'status': 'error', 'msg': 'Amount is required.'}, status=400)

        if not receipt:
            return JsonResponse({'status': 'error', 'msg': 'Receipt image is required.'}, status=400)

        create_topup_request(
            agency=agency,
            amount=amount,
            receipt_image=receipt,
            reference_number=reference
        )

        return JsonResponse({
            'status': 'success',
            'msg': 'Top-Up Request Submitted successfully.'
        })

    except ValidationError as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=400)
    except AttributeError:
        return JsonResponse({'status': 'error', 'msg': 'User has no agency.'}, status=403)
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': f"Server Error: {str(e)}"}, status=500)

# finance/views.py


@login_required
def invoice_detail_ajax(request, invoice_id):
    """
    Returns JSON details for a specific invoice (Items & Breakdown).
    """
    try:
        agency = request.user.managed_agency
        # Secure fetch: Ensure this invoice actually belongs to this agency
        invoice = Invoice.objects.get(id=invoice_id, agency=agency)

        # Get Line Items
        items = invoice.items.all()

        items_data = []
        for item in items:
            items_data.append({
                'description': item.description,
                'amount': intcomma(item.amount),
                'service': str(item.service_object) if item.service_object else "-"
            })

        return JsonResponse({
            'status': 'success',
            'invoice': {
                'number': invoice.invoice_number,
                'status': invoice.status,
                'total': intcomma(invoice.total_amount),
                'date': invoice.created_at.strftime("%b %d, %Y"),
                'due_date': invoice.due_date.strftime("%b %d, %Y") if invoice.due_date else "-"
            },
            'items': items_data
        })

    except Invoice.DoesNotExist:
        return JsonResponse({'status': 'error', 'msg': 'Invoice not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': str(e)}, status=500)


# finance/views.py


@login_required
def download_invoice_pdf(request, invoice_id):
    """
    Generates a PDF using xhtml2pdf (Windows Compatible).
    """
    try:
        agency = request.user.managed_agency
        invoice = Invoice.objects.get(id=invoice_id, agency=agency)

        # 1. Render HTML
        html_string = render_to_string(
            'client/pdf/invoice.html', {'invoice': invoice})

        # 2. Create Response Object
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'

        # 3. Generate PDF
        pisa_status = pisa.CreatePDF(html_string, dest=response)

        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html_string + '</pre>')

        return response

    except Invoice.DoesNotExist:
        return HttpResponse("Invoice not found", status=404)


@login_required
@require_POST
def pay_invoice_ajax(request, invoice_id):
    """
    Allows the client to pay an invoice using their available wallet balance (Gate 2).
    """
    try:
        # 1. Call the Service
        success, message = pay_invoice(
            invoice_id=invoice_id,
            user=request.user
        )

        if success:
            return JsonResponse({'status': 'success', 'msg': 'Invoice paid successfully!'})
        else:
            return JsonResponse({'status': 'error', 'msg': message}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'msg': f"Server Error: {str(e)}"}, status=500)
