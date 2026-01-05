# Assuming you have a basic ProviderForm
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
from django.contrib.auth.decorators import login_required, permission_required
from .models import Port, FerryRequest
from .form import PortForm
from django.shortcuts import render


def admin_ferry_requests_view(request):
    return render(request, 'admin/ferry_requests.html')

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


# client side ------------------------------
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
    print('enter '*10)
    """
    Renders the client booking page.
    Passes the list of active Ferry Providers to the template.
    """
    # providers = Provider.objects.filter(is_active=True)
    providers = Provider.objects.all().order_by('name')
    print(providers)
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

        # C. Validate Form
        form = FerryRequestForm(data)
        if not form.is_valid():
            first_error = next(iter(form.errors.values()))[0]
            return JsonResponse({'status': 'error', 'message': first_error}, status=400)

        # D. Validate Passengers
        passengers = data.get('passengers', [])
        p_error = validate_passenger_structure(passengers)
        if p_error:
            return JsonResponse({'status': 'error', 'message': p_error}, status=400)

        # E. Save
        with transaction.atomic():
            cleaned = form.cleaned_data
            # Safe because form validated it
            route = ProviderRoute.objects.get(pk=cleaned['route_id'])

            req = FerryRequest.objects.create(
                agency=user_agency,
                route=route,
                trip_type=cleaned['trip_type'],
                departure_date=cleaned['departure_date'],
                return_date=cleaned['return_date'],
                accommodation=cleaned['accommodation'],
                passengers_data=passengers,
                vehicle_data=data.get('vehicle', None),  # Can be None
                status='pending'
            )

        return JsonResponse({
            'status': 'success',
            'reference': req.reference,
            'message': 'Request created successfully'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


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
            'price': f"DA {req.selling_price}" if req.selling_price > 0 else "--",
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
            'vehicle': req.vehicle_data
        }
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def respond_to_offer_api(request, reference):
    """
    Handles Client response to an offer (Accept or Reject).
    """
    try:
        req = get_object_or_404(
            FerryRequest, reference=reference, agency=request.user.agency)
        data = json.loads(request.body)
        action = data.get('action')  # 'accept' or 'reject'

        # Security: Can only respond if status is 'offer_sent'
        if req.status != 'offer_sent':
            return JsonResponse({'status': 'error', 'message': 'No pending offer to respond to.'}, status=400)

        if action == 'accept':
            req.status = 'confirmed'
            # Logic hook: Here you might trigger an email or generate PDF invoice
        elif action == 'reject':
            req.status = 'rejected'
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action.'}, status=400)

        req.save()

        return JsonResponse({
            'status': 'success',
            'new_status': req.status,
            'new_label': req.client_status_label
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
