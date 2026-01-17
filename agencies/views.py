from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Agency, AgencyTag
from users.models import CustomUser, Role


@login_required
def agency_management_view(request):
    # 1. Base Query
    base_qs = Agency.objects.select_related(
        'manager').prefetch_related('tags').order_by('-created_at')

    # --- PENDING PAGINATION (4 PER PAGE) ---
    pending_qs = base_qs.filter(status='pending')
    pending_count = pending_qs.count()

    pending_paginator = Paginator(pending_qs, 2)  # <--- Limit 4
    pending_page_num = request.GET.get('pending_page')
    pending_page_obj = pending_paginator.get_page(pending_page_num)

    # --- MAIN LIST FILTERS & PAGINATION ---
    # Default: Exclude pending from the main list unless explicitly searched/filtered
    agencies = base_qs.exclude(status='pending')

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    tag_input = request.GET.get('tag', '').strip()
    balance_filter = request.GET.get('balance', '')

    # Apply Filters to Main List
    if q:
        # If searching, we search everything (including pending)
        agencies = base_qs.filter(
            Q(company_name__icontains=q) |
            Q(rc_number__icontains=q) |
            Q(phone__icontains=q) |
            Q(city__icontains=q) |
            Q(manager__first_name__icontains=q) |
            Q(manager__last_name__icontains=q) |
            Q(manager__email__icontains=q)
        ).distinct()

    if status:
        agencies = agencies.filter(status=status)

    if tag_input:
        tags_list = [t.strip() for t in tag_input.split(',') if t.strip()]
        for t_name in tags_list:
            agencies = agencies.filter(tags__name__icontains=t_name)

    if balance_filter == 'overdraft':
        agencies = agencies.filter(balance__lt=0)
    elif balance_filter == 'positive':
        agencies = agencies.filter(balance__gte=0)

    # Main Pagination (10 per page)
    paginator = Paginator(agencies, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        # Pending Data (Paginated)
        'pending_agencies': pending_page_obj,
        'pending_count': pending_count,

        # Active Data (Paginated)
        'active_agencies': page_obj,
        'total_active': agencies.count(),

        # Filters
        'search_query': q,
        'current_status': status,
        'current_tag': tag_input,
        'current_balance': balance_filter,
        'roles': Role.objects.all(),
    }
    return render(request, 'admin/agencies.html', context)
# --- TRANSACTIONAL CREATE ---


@login_required
@require_POST
def agency_create_api(request):
    try:
        with transaction.atomic():
            data = request.POST

            # 1. Create Agency
            agency = Agency.objects.create(
                company_name=data.get('company_name'),
                rc_number=data.get('rc_number'),
                phone=data.get('agency_phone'),
                city=data.get('city'),
                address=data.get('address'),
                logo=request.FILES.get('logo'),
                rc_document=request.FILES.get('rc_document'),
                status=data.get('status', 'pending'),
                # credit_limit=data.get('credit_limit', 0.00),
                # Balance usually starts at 0, but if migration:
                # balance=data.get('balance', 0.00)
            )

            # 2. Handle Tags
            tag_names = data.get('tags', '').split(',')
            for t_name in tag_names:
                t_name = t_name.strip()
                if t_name:
                    tag, _ = AgencyTag.objects.get_or_create(name=t_name)
                    agency.tags.add(tag)

            # 3. Create Manager User
            role_id = data.get('role')
            role = get_object_or_404(Role, pk=role_id) if role_id else None

            manager = CustomUser.objects.create(
                email=data.get('email'),
                username=data.get('email'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                phone=data.get('manager_phone'),
                state=data.get('state'),
                role=role,
                agency=agency,
                is_active=True
            )

            if data.get('password'):
                manager.set_password(data.get('password'))
            manager.save()

            # 4. Link Manager back to Agency
            agency.manager = manager
            agency.save()

        return JsonResponse({'status': 'success', 'message': 'Agency & Manager created successfully!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# --- UPDATE AGENCY (NO MANAGER) ---


@login_required
@require_POST
def agency_update_api(request, pk):
    try:
        agency = get_object_or_404(Agency, pk=pk)
        data = request.POST

        with transaction.atomic():
            # Update Basic Fields
            agency.company_name = data.get('company_name')
            agency.rc_number = data.get('rc_number')
            agency.phone = data.get('phone')
            agency.city = data.get('city')
            agency.address = data.get('address')
            agency.status = data.get('status')
            agency.credit_limit = data.get('credit_limit')
            # Note: We usually don't update 'balance' manually here,
            # it should be updated via Transactions/Topups, but if you insist:
            # agency.balance = data.get('balance')

            # Files (Only update if new file provided)
            if request.FILES.get('logo'):
                agency.logo = request.FILES.get('logo')
            if request.FILES.get('rc_document'):
                agency.rc_document = request.FILES.get('rc_document')

            agency.save()

            # Update Tags (Clear and Re-add)
            tag_names = data.get('tags', '').split(',')
            agency.tags.clear()
            for t_name in tag_names:
                t_name = t_name.strip()
                if t_name:
                    tag, _ = AgencyTag.objects.get_or_create(name=t_name)
                    agency.tags.add(tag)

        return JsonResponse({'status': 'success', 'message': 'Agency updated successfully!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
