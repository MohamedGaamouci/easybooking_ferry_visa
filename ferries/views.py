from .form import ProviderForm  # Assuming you have a basic ProviderForm
from .models import Provider, ProviderRoute, Port
from django.db import transaction
import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, permission_required
from .models import Port
from .form import PortForm

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
