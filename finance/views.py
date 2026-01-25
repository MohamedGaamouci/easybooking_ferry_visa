from .services.invoice import FinanceService, pay_invoice, serialize_invoices, serialize_ledger, serialize_topups
from xhtml2pdf import pisa  # type: ignore
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import Invoice  # Ensure InvoiceItem is imported
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError

# Services
from .services.account import get_account
from .services.topup import create_topup_request


from django.contrib.humanize.templatetags.humanize import intcomma


# ------------------------------------------------------------
# -------------------- Client Side ---------------------------
# ------------------------------------------------------------


@login_required
def finance_dashboard(request):
    """Initial load endpoint: Loads the HTML shell."""
    try:
        agency = request.user.managed_agency
        account = get_account(agency)
    except AttributeError:
        return render(request, 'errors/no_agency.html')

    # Use Service for stats/topups
    stats, pending_topups = FinanceService.get_initial_dashboard_data(account)

    # FIXED: Call the specific methods instead of the old 'get_filtered_tab_data'
    inv_page = FinanceService.get_invoices(agency, {})
    trans_page = FinanceService.get_ledger(account, {})

    context = {
        'account': account,
        'stats': stats,
        'pending_topups': pending_topups,
        'invoices': inv_page,      # This is for the initial HTML render
        'transactions': trans_page,  # This is for the initial HTML render
    }
    return render(request, 'client/accounting.html', context)


@login_required
def finance_api_router(request):
    agency = request.user.managed_agency
    account = get_account(agency)
    action = request.GET.get('action')

    if action == 'get_invoices':
        page = FinanceService.get_invoices(agency, request.GET)
        return JsonResponse({
            'items': serialize_invoices(page),
            'current_page': page.number,
            'total_pages': page.paginator.num_pages,
            'has_next': page.has_next(),
            'has_prev': page.has_previous(),  # FIXED: was has_prev()
        })

    if action == 'get_ledger':
        page = FinanceService.get_ledger(account, request.GET)
        return JsonResponse({
            'items': serialize_ledger(page),
            'current_page': page.number,
            'total_pages': page.paginator.num_pages,
            'has_next': page.has_next(),
            'has_prev': page.has_previous(),  # FIXED: was has_prev()
        })
    if action == 'get_topups':
        page = FinanceService.get_topup_history(account, request.GET)
        return JsonResponse({
            'items': serialize_topups(page),
            'current_page': page.number,
            'total_pages': page.paginator.num_pages,
            'has_next': page.has_next(),
            'has_prev': page.has_previous(),
        })

# ============================================


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
