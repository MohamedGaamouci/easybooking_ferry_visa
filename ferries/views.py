# Assuming you have a basic ProviderForm
# Ensure you have this from previous steps
from ferries.services.ferry_services import FerryPricingService, FerryScheduleService, FerryPriceAdminService
from ferries.models.provider_route import RoutePriceComponent, RouteSchedule
from .models import FerryRequest
from finance.services.invoice import create_single_service_invoice
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from .models import FerryRequest
from django.db.models import Q
from django.core.paginator import Paginator
from .form import FerryRequestForm, validate_passenger_structure
from .models import FerryRequest, ProviderRoute
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .form import ProviderForm, FerryRequestForm
from .models import Provider, ProviderRoute, Port
from django.db import transaction
import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from .models import Port, FerryRequest
from .form import PortForm
from django.shortcuts import render


# --- CREATE PORT ---


@login_required
@require_POST
def port_create_view(request):
    try:
        # We use request.POST directly since it's a simple form (not nested JSON)
        form = PortForm(request.POST)

        if form.is_valid():
            port = form.save()
            return JsonResponse({'status': 'success', 'message': f"Port '{port.name}' created successfully!"})
        else:
            # Return the first error found
            first_error = next(iter(form.errors.values()))[0]
            return JsonResponse({'status': 'error', 'message': first_error}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# --- UPDATE PORT ---


@login_required
@require_POST
def port_update_view(request, pk):
    try:
        port = get_object_or_404(Port, pk=pk)
        form = PortForm(request.POST, instance=port)

        if form.is_valid():
            port = form.save()
            return JsonResponse({'status': 'success', 'message': f"Port '{port.name}' updated successfully!"})
        else:
            first_error = next(iter(form.errors.values()))[0]
            return JsonResponse({'status': 'error', 'message': first_error}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# --- GET PORT DETAILS (For Edit Modal) ---
@login_required
def port_detail_api(request, pk):
    try:
        port = get_object_or_404(Port, pk=pk)
        data = {
            'status': 'success',
            'port': {
                'id': port.id,
                'name': port.name,
                'code': port.code,
                'city': port.city,
                'country': port.country,
                'is_active': port.is_active
            }
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# --- HELPER: GET PROVIDER DETAILS + ROUTES ---

@login_required
def provider_detail_api(request, pk):
    try:
        prov = get_object_or_404(Provider, pk=pk)

        # Get Routes
        routes = []
        for r in prov.routes.all():
            routes.append({
                'id': r.id,
                'origin_id': r.origin.id,
                'destination_id': r.destination.id,
                'is_active': r.is_active,
                'notes': r.notes
            })

        data = {
            'status': 'success',
            'provider': {
                'id': prov.id,
                'name': prov.name,
                'code': prov.code,
                'contact_email': prov.contact_email,
                'contact_phone': prov.contact_phone,
                'is_active': prov.is_active,
                # JSON serializable logo URL
                'logo_url': prov.logo.url if prov.logo else None
            },
            'routes': routes
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# --- CREATE / UPDATE PROVIDER (With Routes) ---


@login_required
@require_POST
def provider_save_view(request, pk=None):
    """
    Handles BOTH Create (pk=None) and Update (pk provided).
    Expects multipart/form-data with 'routes_json' string.
    """
    try:
        if pk:
            provider = get_object_or_404(Provider, pk=pk)
            form = ProviderForm(request.POST, request.FILES, instance=provider)
        else:
            provider = None
            form = ProviderForm(request.POST, request.FILES)

        if not form.is_valid():
            return JsonResponse({'status': 'error', 'message': f"Form Error: {form.errors.as_text()}"}, status=400)

        # Parse Routes JSON
        routes_json = request.POST.get('routes_json', '[]')
        try:
            routes_data = json.loads(routes_json)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': "Invalid JSON for routes"}, status=400)

        with transaction.atomic():
            # 1. Save Provider
            provider = form.save()

            # 2. Sync Routes (Update, Create, Delete Missing)

            # A. Get IDs of routes kept in the UI
            incoming_ids = [int(r['id']) for r in routes_data if r.get('id')]

            # B. Delete routes that are NOT in the incoming list
            # (If user removed a row in UI, we remove it from DB)
            provider.routes.exclude(id__in=incoming_ids).delete()

            # C. Update or Create
            for r_data in routes_data:
                origin = get_object_or_404(Port, pk=r_data['origin_id'])
                destination = get_object_or_404(
                    Port, pk=r_data['destination_id'])

                # Validation: Origin != Destination
                if origin == destination:
                    continue  # Skip invalid route

                route_id = r_data.get('id')
                if route_id:
                    # Update
                    route = ProviderRoute.objects.get(
                        pk=route_id, provider=provider)
                    route.origin = origin
                    route.destination = destination
                    route.is_active = r_data['is_active']
                    route.notes = r_data.get('notes', '')
                    route.save()
                else:
                    # Create
                    ProviderRoute.objects.create(
                        provider=provider,
                        origin=origin,
                        destination=destination,
                        is_active=r_data['is_active'],
                        notes=r_data.get('notes', '')
                    )

        action = "updated" if pk else "created"
        return JsonResponse({'status': 'success', 'message': f"Provider {action} successfully!"})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# ------------------------------------------------------------ client side ------------------------------------------------------------
# ------------------------------------------------------------ client side ------------------------------------------------------------
# ------------------------------------------------------------ client side ------------------------------------------------------------
@login_required
def ferries_view(request):
    """
    Renders the 'My Requests' page.
    Passes 'providers' so we can build the filter dropdown in HTML.
    """
    # Import locally to avoid circular imports if needed
    from .models import Provider

    # Fetch active providers for the filter dropdown
    providers = Provider.objects.filter(is_active=True).values('id', 'name')

    return render(request, 'client/ferry_requests.html', {'providers': providers})


# Helper for JSON validation (keep it simple inside the view or utils)
def validate_passenger_structure(data):
    if not isinstance(data, list) or not data:
        return "Passenger list cannot be empty."
    for p in data:
        if not all(k in p for k in ('first_name', 'last_name', 'type')):
            return "Invalid passenger data structure."
    return None


@login_required
def new_demand_view(request):
    """
    Renders the client booking page.
    Passes the list of active Ferry Providers to the template.
    """
    # providers = Provider.objects.filter(is_active=True)
    providers = Provider.objects.filter(is_active=True).order_by('name')
    return render(request, 'client/new_ferry.html', {'providers': providers})


@login_required
@require_GET
def get_provider_routes_api(request, provider_id):
    """
    API: Returns valid routes for a specific provider.
    Used by the frontend to populate Origin/Destination dropdowns.
    """
    routes = ProviderRoute.objects.filter(
        provider_id=provider_id, is_active=True).select_related('origin', 'destination')

    data = []
    for r in routes:
        data.append({
            'route_id': r.id,
            'origin_code': r.origin.code,
            'origin_name': r.origin.name,
            'dest_code': r.destination.code,
            'dest_name': r.destination.name
        })

    return JsonResponse({'status': 'success', 'routes': data})


# ==========================================
# 1. CREATE METHOD
# ==========================================

@login_required
@require_POST
def create_ferry_request_api(request):
    try:
        # A. Parse JSON
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)

        # B. Get Agency (Security)
        user_agency = getattr(request.user, 'agency', None)
        if not user_agency:
            return JsonResponse({'status': 'error', 'message': 'You must be logged in as an Agency Manager.'}, status=403)

        # C. Validate Form (Includes Schedule Validation)
        form = FerryRequestForm(data)
        if not form.is_valid():
            first_error = next(iter(form.errors.values()))[0]
            return JsonResponse({'status': 'error', 'message': first_error}, status=400)

        # D. Validate Passenger Structure
        passengers = data.get('passengers', [])
        p_error = validate_passenger_structure(passengers)
        if p_error:
            return JsonResponse({'status': 'error', 'message': p_error}, status=400)

        # E. NEW: Atomic Pricing Calculation
        # This calculates the price server-side so it cannot be manipulated by the client
        try:
            pricing_result = FerryPricingService.calculate_total_price(
                route_id=data['route_id'],
                travel_date=data['departure_date'],
                passengers=passengers,
                vehicle=data.get('vehicle'),
                accommodation=data.get('accommodation')
            )
        except ValidationError as ve:
            return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)

        # F. Save with Atomic Transaction
        with transaction.atomic():
            cleaned = form.cleaned_data
            route = ProviderRoute.objects.get(pk=cleaned['route_id'])

            req = FerryRequest.objects.create(
                agency=user_agency,
                route=route,
                trip_type=cleaned['trip_type'],
                departure_date=cleaned['departure_date'],
                return_date=cleaned['return_date'],
                accommodation=cleaned['accommodation'],
                passengers_data=passengers,
                vehicle_data=data.get('vehicle', None),

                # Dynamic Pricing Data
                net_price=pricing_result['total_net'],
                selling_price=pricing_result['total_selling'],
                # breakdown is stored to keep a record of prices at time of booking
                price_breakdown=pricing_result['breakdown'],

                status='pending',
                requested_by=request.user
            )

        return JsonResponse({
            'status': 'success',
            'reference': req.reference,
            'message': 'Request created successfully',
            'total_price': float(req.selling_price)
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"System Error: {str(e)}"}, status=500)
# ==========================================
# 2. UPDATE METHOD
# ==========================================


@login_required
@require_POST
def update_ferry_request_api(request, reference):
    """
    Updates an existing request using its Reference (e.g. 'FER-93821')
    """
    try:
        # A. Find Request & Check Ownership
        req_obj = get_object_or_404(FerryRequest, reference=reference)

        # Security: Ensure the logged-in agency owns this request
        if req_obj.agency != getattr(request.user, 'agency', None):
            return JsonResponse({'status': 'error', 'message': 'Permission denied. You do not own this request.'}, status=403)

        # Logic: Prevent editing if already processing/confirmed
        if req_obj.status != 'pending':
            return JsonResponse({'status': 'error', 'message': f'Cannot edit request in "{req_obj.status}" status.'}, status=400)

        # B. Parse Data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)

        # C. Validate Form (Pass instance? No, because we use JSON data, just validate logic)
        form = FerryRequestForm(data)
        if not form.is_valid():
            first_error = next(iter(form.errors.values()))[0]
            return JsonResponse({'status': 'error', 'message': first_error}, status=400)

        # D. Validate Passengers
        passengers = data.get('passengers', [])
        p_error = validate_passenger_structure(passengers)
        if p_error:
            return JsonResponse({'status': 'error', 'message': p_error}, status=400)

        # E. Update Object
        with transaction.atomic():
            cleaned = form.cleaned_data

            # Update Fields
            req_obj.route = ProviderRoute.objects.get(pk=cleaned['route_id'])
            req_obj.trip_type = cleaned['trip_type']
            req_obj.departure_date = cleaned['departure_date']
            req_obj.return_date = cleaned['return_date']
            req_obj.accommodation = cleaned['accommodation']

            # Update JSON Fields
            req_obj.passengers_data = passengers
            req_obj.vehicle_data = data.get('vehicle', None)

            req_obj.save()

        return JsonResponse({
            'status': 'success',
            'reference': req_obj.reference,
            'message': 'Request updated successfully'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_GET
def get_client_requests_api(request):
    """
    API to retrieve filtered, searched, and paginated requests for the Data Table.
    """
    # 1. Base Query: ONLY show requests for this user's agency
    user_agency = getattr(request.user, 'agency', None)
    if not user_agency:
        return JsonResponse({'status': 'error', 'message': 'No agency assigned.'}, status=403)

    qs = FerryRequest.objects.filter(agency=user_agency).select_related(
        'route', 'route__provider').order_by('-created_at')

    # 2. Search (Reference OR Passenger Name)
    search_query = request.GET.get('search', '').strip()
    if search_query:
        # Search inside Reference OR the JSON text for passengers
        qs = qs.filter(
            Q(reference__icontains=search_query) |
            Q(passengers_data__icontains=search_query)
        )

    # 3. Filter: Status
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        qs = qs.filter(status=status_filter)

    # 4. Filter: Date Range (Departure)
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        qs = qs.filter(departure_date__gte=date_from)
    if date_to:
        qs = qs.filter(departure_date__lte=date_to)

    # 5. Filter: Provider/Route (Optional)
    provider_id = request.GET.get('provider')
    if provider_id:
        qs = qs.filter(route__provider_id=provider_id)

    # 6. Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(qs, 10)  # Show 10 per page
    page_obj = paginator.get_page(page_number)

    # 7. Serialize Data
    data = []
    for req in page_obj:
        # Helper to get first passenger name safely
        first_p = "Unknown"
        if req.passengers_data and len(req.passengers_data) > 0:
            p = req.passengers_data[0]
            first_p = f"{p.get('first_name', '')} {p.get('last_name', '')}"
            more_count = len(req.passengers_data) - 1
            if more_count > 0:
                first_p += f" (+{more_count})"

        data.append({
            'id': req.id,
            'reference': req.reference,
            'status': req.status,
            'status_label': req.client_status_label,  # Uses the property from your model
            'provider_name': req.route.provider.name,
            'route_str': f"{req.route.origin.code} ↔ {req.route.destination.code}",
            'departure': req.departure_date.strftime('%d %b %Y'),
            'passenger_summary': first_p,
            'price': f"{req.selling_price} DA" if req.selling_price > 0 else "--",
            'created_at': req.created_at.strftime('%Y-%m-%d')
        })

    return JsonResponse({
        'status': 'success',
        'data': data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_items': paginator.count
        }
    })


# ferries/views.py
@login_required
@require_GET
def get_ferry_request_detail_api(request, reference):
    try:
        req = get_object_or_404(
            FerryRequest, reference=reference, agency=request.user.agency)

        data = {
            'reference': req.reference,
            'status': req.status,
            'status_label': req.client_status_label,
            'trip_type': req.trip_type,
            'departure_date': req.departure_date,
            'return_date': req.return_date,
            'accommodation': req.accommodation,

            # Logic: Only show price if it's set (not 0.00)
            'selling_price': str(req.selling_price) if req.selling_price > 0 else None,

            # Logic: Send Voucher URL if it exists
            'voucher_url': req.voucher.url if req.voucher else None,

            'provider_name': req.route.provider.name,
            'route_id': req.route.id,
            'route_str': f"{req.route.origin.code} ↔ {req.route.destination.code}",

            'passengers': req.passengers_data,
            'vehicle': req.vehicle_data,
            'admin_note': req.admin_note,
        }
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# Import the Finance Service


@login_required
@require_POST
def respond_to_offer_api(request, reference):
    """
    Handles Client response to an offer (Accept or Reject).
    If Accepted, it triggers Gate 1 (Credit Check) and Generates an Invoice.
    """
    try:
        # 1. Parse Data
        req = get_object_or_404(
            FerryRequest, reference=reference, agency=request.user.agency)
        data = json.loads(request.body)
        action = data.get('action')  # 'accept' or 'reject'

        # Security: Can only respond if status is 'offer_sent'
        if req.status != 'offer_sent':
            return JsonResponse({'status': 'error', 'message': 'No pending offer to respond to.'}, status=400)

        with transaction.atomic():
            if action == 'accept':
                # ====================================================
                # GENERATE INVOICE & CHECK CREDIT (GATE 1)
                # ====================================================

                # Ensure the offer has a valid price
                # (Assuming your model has a field like 'offer_price' or 'total_price')
                price = req.selling_price

                if not price or price <= 0:
                    raise ValidationError(
                        "Invalid offer price. Cannot generate invoice.")

                # Call the Finance Service
                # This AUTOMATICALLY checks Credit Limit and Reserves Funds
                invoice = create_single_service_invoice(
                    service_object=req,
                    amount=price,
                    description=f"Ferry Booking: {req.route} ({req.departure_date})",
                    user=request.user
                )

                # Link Invoice & Update Status
                req.invoice = invoice
                req.status = 'confirmed'
                req.save()

                msg = "Offer accepted and Invoice generated."

            elif action == 'reject':
                req.status = 'rejected'
                req.save()
                msg = "Offer rejected."

            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid action.'}, status=400)

        return JsonResponse({
            'status': 'success',
            'message': msg,
            'new_status': req.status,
            'new_label': req.get_status_display()  # Helper to show nice text
        })

    except ValidationError as ve:
        # This catches "Credit Limit Reached" from the finance service
        # Sends a clear error message to the frontend so they know why they can't accept
        error_msg = ve.message if hasattr(ve, 'message') else str(ve)
        return JsonResponse({'status': 'error', 'message': error_msg}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"System Error: {str(e)}"}, status=500)


# ------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------


# ==========================================
# 1. ADMIN: LIST & STATS API
# ==========================================
@login_required
@require_GET
def get_admin_requests_api(request):
    """
    Returns data for the Admin Dashboard: Stats + Paginated List
    """
    # 1. Base Query
    qs = FerryRequest.objects.all().select_related(
        'agency', 'route', 'route__provider').order_by('-created_at')

    # 2. Search (Ref, Agency Name, Provider)
    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(reference__icontains=search) |
            Q(agency__company_name__icontains=search) |
            Q(route__provider__name__icontains=search)
        )

    # 3. Calculate Stats (Live Data based on current Search)
    # We calculate stats BEFORE filtering by status so the cards always show totals
    stats = {
        'new': qs.filter(status='pending').count(),
        'pending_offer': qs.filter(status='offer_sent').count(),
        'confirmed': qs.filter(status='confirmed').count(),
        # Calculate revenue (Sum of selling_price for confirmed requests today/total)
        'revenue': qs.filter(status='confirmed').aggregate(total=Sum('selling_price'))['total'] or 0
    }

    # 4. Status Filter (For the Table Only)
    # This comes from the JS: setFilter('pending'), setFilter('confirmed'), etc.
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        qs = qs.filter(status=status_filter)

    # 5. Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(page_number)

    # 6. Serialize List
    data = []
    for req in page_obj:
        # User handling safety check
        requested_by = req.requested_by.get_full_name() if req.requested_by else "Unknown"
        user_admin = req.user_admin.get_full_name() if req.user_admin else "Unknown"

        data.append({
            'id': req.id,
            'reference': req.reference,
            'agency_name': req.agency.company_name,
            'agency_user': requested_by,
            'provider_name': req.route.provider.name,
            'route_str': f"{req.route.origin.code} ↔ {req.route.destination.code}",
            'trip_type': req.get_trip_type_display(),
            'departure': req.departure_date.strftime('%d %b %Y'),
            'pax_count': len(req.passengers_data),
            'status': req.status,
            'status_label': req.admin_status_label,  # Use the property from model
            'created_ago': req.created_at.strftime('%H:%M %d/%m'),
            'user_admin': user_admin,
            'admin_note': req.admin_note
        })

    return JsonResponse({
        'status': 'success',
        'stats': stats,
        'data': data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_items': paginator.count
        }
    })
# ==========================================
# 2. ADMIN: PAGE VIEWS
# ==========================================


@login_required
def admin_requests_view(request):
    """Renders the HTML List Page"""
    return render(request, 'admin/incoming_requests.html')


@login_required
def admin_process_view(request, reference):
    """Renders the Detail/Process Page (Server-Side Render for initial details)"""
    req = get_object_or_404(FerryRequest, reference=reference)

    user = request.user

    # is_agency_user = hasattr(user, 'agency')

    # print('is agency user:: ', is_agency_user)
    # print(user)

    if (user.is_authenticated and req.status == 'pending'):
        req.status = 'processing'
        req.save(update_fields=['status'])

    # We pass the object directly to the template for easy rendering
    context = {
        'req': req,
        'passenger_count': len(req.passengers_data),
        'has_vehicle': bool(req.vehicle_data)
    }
    return render(request, 'admin/process_request.html', context)

# ==========================================
# 3. ADMIN: ACTIONS (Send Offer)
# ==========================================


@login_required
@require_POST
def admin_send_offer_api(request, reference):
    """
    Updates pricing and moves status to 'offer_sent'
    """
    try:
        req = get_object_or_404(FerryRequest, reference=reference)
        data = json.loads(request.body)

        net_price = data.get('net_price')
        sell_price = data.get('sell_price')
        notes = data.get('note')  # Optional admin notes

        try:
            sell_price = float(sell_price)
            net_price = float(net_price)
        except (TypeError, ValueError):
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid price format.'},
                status=400
            )

        if sell_price <= 0:
            return JsonResponse(
                {'status': 'error', 'message': 'Selling price must be greater than 0.'},
                status=400
            )

        if net_price <= 0:
            return JsonResponse(
                {'status': 'error', 'message': 'Net price must be greater than 0.'},
                status=400
            )

        if sell_price <= net_price:
            return JsonResponse({'status': 'error', 'message': "Selling price can't be less than or equal net price."}, status=400)

        # Update Logic
        req.net_price = net_price
        req.selling_price = sell_price
        req.status = 'offer_sent'
        # You could save 'notes' to a new field in model if needed
        admin_user = request.user
        if getattr(admin_user, 'agency', None):
            return JsonResponse({'status': "error", 'message': 'You Are not Authorized to send offer (you must be admin stuff)'})

        req.admin_note = notes
        req.user_admin = admin_user

        req.save()

        return JsonResponse({'status': 'success', 'message': 'Offer sent successfully.'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def admin_reject_request(request, pk):
    """
    Updates pricing and moves status to 'offer_sent'
    """
    try:
        req = get_object_or_404(FerryRequest, pk=pk)
        data = json.loads(request.body)
        if req.status in ['confirmed', 'rejected', 'cancelled']:
            return JsonResponse({"status": 'error', 'message': f'The status is already in {req.status}'})
        req.status = 'rejected'
        req.admin_note = data.get('note')
        # You could save 'notes' to a new field in model if needed

        req.save()

        return JsonResponse({'status': 'success', 'message': 'Offre Rejected successefully.'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def api_attach_voucher(request):
    """
    Handles voucher file upload for a specific Ferry Request.
    1. Validates file size (Max 5MB).
    2. Saves the file.
    3. Updates status to 'ready'.
    """
    req_id = request.POST.get('request_id')
    voucher = request.FILES.get('voucher_file')

    # 1. Basic Validation
    if not req_id or not voucher:
        return JsonResponse({'status': 'error', 'message': 'Missing request ID or file.'})

    # 2. Size Validation (Backend Security Check)
    # 5MB = 5 * 1024 * 1024 bytes
    if voucher.size > 5 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'message': 'File is too large. Max size is 5MB.'})

    try:
        # 3. Get the Request
        ferry_req = FerryRequest.objects.get(id=req_id)

        # 4. Save the File
        # Django handles the file system storage automatically here
        ferry_req.voucher = voucher

        ferry_req.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Voucher attached and request marked as Ready.'
        })

    except FerryRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Request not found.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# ==========================================
#  Add Route Dates and price componenets
# ==========================================

# --- CLIENT SIDE APIS ---


@login_required
@require_GET
def get_available_dates_api(request, route_id):
    """
    API: Returns a list of strings ['YYYY-MM-DD'] representing available trips.
    Used by the frontend datepicker to enable specific dates.
    """
    try:
        available_dates = FerryPricingService.get_available_dates(route_id)
        # Convert date objects to strings for JSON
        date_strings = [d.strftime('%Y-%m-%d') for d in available_dates]
        return JsonResponse({'status': 'success', 'dates': date_strings})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def validate_and_calculate_price_api(request):
    """
    API: Receives current form selection (one-way or round-trip)
    Returns a live price breakdown for both legs.
    """
    try:
        data = json.loads(request.body)
        route_id = data.get('route_id')
        departure_date = data.get('departure_date')
        return_date = data.get('return_date')  # Might be None
        passengers = data.get('passengers', [])
        vehicle = data.get('vehicle', None)

        if not route_id or not departure_date:
            return JsonResponse({'status': 'error', 'message': 'Missing route or date.'}, status=400)

        # 1. Calculate Outbound Price
        # We assume 'accommodation' in the passenger object is the outbound choice
        outbound_result = FerryPricingService.calculate_total_price(
            route_id=route_id,
            travel_date=departure_date,
            passengers=passengers,
            vehicle=vehicle
        )

        final_result = {
            'total_net': outbound_result['total_net'],
            'total_selling': outbound_result['total_selling'],
            'breakdown': outbound_result['breakdown']
        }

        # 2. If Round Trip, Calculate Return Price
        if return_date:
            # Find the reverse route (B -> A)
            forward_route = get_object_or_404(ProviderRoute, pk=route_id)
            reverse_route = ProviderRoute.objects.filter(
                provider=forward_route.provider,
                origin=forward_route.destination,
                destination=forward_route.origin
            ).first()

            if reverse_route:
                # Map return_accommodation choices to the passenger list
                return_passengers = []
                for p in passengers:
                    return_passengers.append({
                        'type': p['type'],
                        'accommodation': p.get('return_accommodation')
                    })

                return_result = FerryPricingService.calculate_total_price(
                    route_id=reverse_route.id,
                    travel_date=return_date,
                    passengers=return_passengers,
                    vehicle=vehicle  # Assume same vehicle for return
                )

                # Combine the totals and breakdowns
                final_result['total_net'] += return_result['total_net']
                final_result['total_selling'] += return_result['total_selling']

                # Tag return items for clarity in the frontend panel
                return_breakdown = []
                for item in return_result['breakdown']:
                    item['item'] = f"(Return) {item['item']}"
                    return_breakdown.append(item)

                final_result['breakdown'].extend(return_breakdown)

        return JsonResponse({'status': 'success', 'pricing': final_result})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_GET
def get_route_options_api(request, route_id):
    """
    API: Returns unique Accommodation and Vehicle types available for a route.
    Used to populate frontend dropdowns dynamically.
    """
    try:
        # Fetch all pricing rules for this route
        components = RoutePriceComponent.objects.filter(route_id=route_id)

        # Extract unique item names by category
        accommodations = list(components.filter(category='accommodation')
                              .values_list('item_name', flat=True).distinct())

        vehicles = list(components.filter(category='vehicle')
                        .values_list('item_name', flat=True).distinct())

        # We also return Passenger types in case you want to dynamicize those manifest labels later
        passengers = list(components.filter(category='pax')
                          .values_list('item_name', flat=True).distinct())

        return JsonResponse({
            'status': 'success',
            'accommodations': accommodations,
            'vehicles': vehicles,
            'passenger_types': passengers
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# --- ADMIN SIDE APIS (CRUD) ---


@login_required
@require_POST
def admin_manage_schedule_api(request, route_id):
    """
    API: Bulk add dates to a route schedule.
    Expects JSON: {"dates": ["2026-06-01", "2026-06-08"]}
    """
    # if hasattr(request.user, 'agency'):  # Security: Prevent non-staff from access
    #     return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        dates = data.get('dates', [])  # This is your array from selectedDates

        with transaction.atomic():
            # 1. Clear the old schedule for this specific route
            RouteSchedule.objects.filter(route_id=route_id).delete()

            # 2. Add the new "Final Truth" list
            if dates:
                FerryScheduleService.bulk_add_dates(route_id, dates)

        return JsonResponse({
            'status': 'success',
            'message': f'Schedule synchronized. {len(dates)} dates active.'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def admin_save_price_component_api(request, route_id):
    """
    API: Create or update a price component.
    """
    # if hasattr(request.user, 'agency'):
    #     return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        # This calls your Atomic service method
        price_item = FerryPriceAdminService.create_or_update_price(
            route_id, data)
        return JsonResponse({'status': 'success', 'message': 'Price saved successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# --- ADMIN SCHEDULE MANAGEMENT ---


@login_required
def get_admin_route_calendar_api(request, route_id):
    """
    API: Returns all scheduled dates for a route so the admin can see them in a list/table.

    """
    # if hasattr(request.user, 'agency'):
    #     print("curret user: ", request.user)
    #     print('has agency: ', hasattr(request.user, 'agency'))
    #     print(getattr(request.user, 'agency'))
    #     return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    try:
        # Use the service to get the ordered queryset
        schedules = FerryScheduleService.get_route_calendar(route_id)

        data = [{
            'id': s.id,
            'date': s.date.strftime('%Y-%m-%d'),
            'is_active': s.is_active
        } for s in schedules]

        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def delete_schedule_date_api(request, schedule_id):
    """
    API: Removes a specific date from the schedule.

    """
    # if hasattr(request.user, 'agency'):
    #     return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    try:
        # The service method uses @transaction.atomic internally
        deleted_count, _ = FerryScheduleService.delete_date(schedule_id)

        if deleted_count > 0:
            return JsonResponse({'status': 'success', 'message': 'Date removed from schedule.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Schedule entry not found.'}, status=404)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def get_pricing_structure_api(request):
    """
    Returns Providers -> Routes for the management tab.
    """
    providers = Provider.objects.filter(is_active=True).prefetch_related(
        'routes__origin', 'routes__destination')

    data = []
    for p in providers:
        routes = [{
            'id': r.id,
            'origin': r.origin.code,
            'destination': r.destination.code,
            'is_active': r.is_active
        } for r in p.routes.all()]

        data.append({
            'id': p.id,
            'name': p.name,
            'logo': p.logo.url if p.logo else None,
            'routes': routes
        })
    return JsonResponse({'status': 'success', 'data': data})


@login_required
def get_route_pricing_api(request, route_id):
    """
    API: Returns all price rules for a specific route.
    Uses FerryPriceAdminService.get_route_pricing_grid
    """
    # if hasattr(request.user, 'agency'):
    #     return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    try:
        # Using your service method
        components = FerryPriceAdminService.get_route_pricing_grid(route_id)

        data = [{
            'id': c.id,
            'category': c.category,  # 'pax', 'vehicle', etc.
            'item_name': c.item_name,
            'start_date': c.start_date.strftime('%Y-%m-%d'),
            'end_date': c.end_date.strftime('%Y-%m-%d'),
            'net_price': float(c.net_price),
            'selling_price': float(c.selling_price)
        } for c in components]

        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def delete_price_component_api(request, component_id):
    """
    API: Deletes a specific price rule.
    Uses FerryPriceAdminService.delete_price_component
    """
    # if hasattr(request.user, 'agency'):
    #     return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    try:
        # Using your atomic service method
        deleted_count, _ = FerryPriceAdminService.delete_price_component(
            component_id)

        if deleted_count > 0:
            return JsonResponse({'status': 'success', 'message': 'Price component deleted.'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Component not found.'}, status=404)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
