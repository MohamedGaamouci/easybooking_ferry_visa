from .permissions_utils import ADMIN_ENDPOINTS, CLIENT_ENDPOINTS
from django.db import models
from django.shortcuts import redirect
from django.shortcuts import render
from django.contrib.auth import get_user_model
from agencies.models import Agency
from .models import Role  # Assuming Role is in the users app
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import models  # Needed for models.Count
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import Role

from django.db.models import Q
from .models import CustomUser, Role
from agencies.models import Agency  # Assuming your Agency model is here
from .form import UserForm


@login_required
def user_management_view(request):
    # 1. Base Query
    users = CustomUser.objects.select_related(
        'role', 'agency').order_by('-date_joined')

    # 2. Filtering
    search_query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    agency_filter = request.GET.get('agency', '')
    status_filter = request.GET.get('status', '')

    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(agency__company_name__icontains=search_query)
        )

    if role_filter:
        users = users.filter(role_id=role_filter)

    if agency_filter:
        if agency_filter == 'none':
            users = users.filter(agency__isnull=True)
        else:
            users = users.filter(agency_id=agency_filter)

    if status_filter:
        if status_filter == 'active':
            users = users.filter(is_active=True)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)

    # 3. Context Data for Dropdowns
    roles = Role.objects.all()
    agencies = Agency.objects.filter(status=True)  # Only show active agencies

    context = {
        'users': users,
        'roles': roles,
        'agencies': agencies,
        # Keep filters in UI after reload
        'search_query': search_query,
        'current_role': role_filter,
        'current_agency': agency_filter,
        'current_status': status_filter,
    }

    return render(request, 'admin/users.html', context)

# --- API: GET USER DETAILS (For Edit Modal) ---


@login_required
def user_detail_api(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    data = {
        'status': 'success',
        'user': {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': user.phone,
            'state': user.state,
            'role_id': user.role.id if user.role else '',
            'agency_id': user.agency.id if user.agency else '',
            'is_active': user.is_active
        }
    }
    return JsonResponse(data)

# --- VIEW: ROLE MANAGEMENT PAGE ---


@login_required
@require_POST
def user_save_view(request, pk=None):
    try:
        # Check if creating (pk=None) or updating
        if pk:
            user = get_object_or_404(CustomUser, pk=pk)
            form = UserForm(request.POST, instance=user)
            agency = user.agency
        else:
            user = None
            form = UserForm(request.POST)

        if form.is_valid():
            user_obj = form.save(commit=False)

            # Hash password if provided
            raw_password = form.cleaned_data.get('password')
            if raw_password:
                user_obj.set_password(raw_password)

            # Username = Email
            user_obj.username = user_obj.email
            if pk:
                user_obj.agency = agency
            user_obj.save()

            action = "updated" if pk else "created"
            return JsonResponse({'status': 'success', 'message': f"User {action} successfully!"})
        else:
            return JsonResponse({'status': 'error', 'message': f"Form Error: {form.errors.as_text()}"}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def login_success_router(request):
    """
    Redirects users based on their assigned Role name.
    """
    user = request.user

    # 1. Check if the user has a Role assigned
    if hasattr(user, 'agency') and user.agency is not None:
        return redirect('client_dashboard')

    # 3. Fallback: Everyone else (Platform Manager, Finance, Superuser) -> Admin Panel
    return redirect('admin_dashboard')


def sync_permissions_to_db():
    """Helper to ensure every endpoint in utils.py exists as a Permission in DB"""
    content_type = ContentType.objects.get_for_model(Role)
    for mapping in [ADMIN_ENDPOINTS, CLIENT_ENDPOINTS]:
        for category, url_names in mapping.items():
            for url_name in url_names:
                codename = f"access_{url_name}"
                Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type,
                    defaults={
                        'name': f"Access {url_name.replace('_', ' ').title()}"}
                )


@login_required
def role_management_view(request):
    # Determine if we are looking at ADMIN roles or AGENCY roles
    # Use: /admin_panel/roles/?side=ADMIN
    side = request.GET.get('side', 'ADMIN')

    # 1. Sync dictionary to DB
    sync_permissions_to_db()

    # 2. Get roles belonging to this side only
    roles = Role.objects.filter(category=side).annotate(
        user_count=models.Count('customuser')
    )

    # 3. Get the correct dictionary from your utils.py
    endpoint_map = ADMIN_ENDPOINTS if side == 'ADMIN' else CLIENT_ENDPOINTS

    # 4. Group the database Permission objects for the template checkboxes
    grouped_permissions = {}
    for category, url_names in endpoint_map.items():
        codenames = [f"access_{name}" for name in url_names]
        # Fetch the actual Permission objects so we have their IDs
        perms = Permission.objects.filter(codename__in=codenames)
        grouped_permissions[category] = perms

    context = {
        'roles': roles,
        'grouped_permissions': grouped_permissions,
        'current_side': side
    }
    return render(request, 'admin/roles.html', context)


@login_required
def role_detail_api(request, pk):
    role = get_object_or_404(Role, pk=pk)
    return JsonResponse({
        'status': 'success',
        'role': {
            'id': role.id,
            'name': role.name,
            'description': role.description,
            'permissions': list(role.permissions.values_list('id', flat=True))
        }
    })


@login_required
@require_POST
def role_save_view(request, pk=None):
    try:
        data = request.POST
        name = data.get('name')
        description = data.get('description')
        # This category field is crucial for the "Derived" logic
        category = data.get('category', 'AGENCY')
        perm_ids = data.getlist('permissions[]')

        if pk:
            role = get_object_or_404(Role, pk=pk)
            role.name = name
            role.description = description
            role.save()
        else:
            role = Role.objects.create(
                name=name,
                description=description,
                category=category
            )

        role.permissions.set(perm_ids)
        return JsonResponse({'status': 'success', 'message': 'Role saved successfully!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
