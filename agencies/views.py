from django.shortcuts import render
from django.db.models import Sum
from .models import Agency
from finance.models import Account
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse


def admin_agencies_view(request):
    """
    Renders the Agency Management page with separate lists for Pending and Active agencies.
    """
    # 1. Fetch all agencies optimized
    all_agencies = Agency.objects.select_related(
        'account').all().order_by('-created_at')

    # 2. Separate them
    pending_agencies = all_agencies.filter(status='pending')
    active_agencies = all_agencies.exclude(status='pending')

    # 3. Calculate Stats
    total_active = active_agencies.count()
    pending_count = pending_agencies.count()

    # Calculate Total Wallet Balance of ACTIVE agencies
    total_balance = Account.objects.filter(agency__in=active_agencies).aggregate(
        Sum('balance'))['balance__sum'] or 0

    # Count Critical Low Balances
    low_balance_count = Account.objects.filter(
        balance__lt=5000, agency__in=active_agencies).count()

    context = {
        'pending_agencies': pending_agencies,
        'active_agencies': active_agencies,
        'pending_count': pending_count,
        'total_active': total_active,
        'total_balance': total_balance,
        'low_balance_count': low_balance_count,
    }

    return render(request, 'admin/agencies.html', context)


@login_required
@require_GET
def get_agencies_api(request):
    """
    API: Returns a list of active agencies for the dropdown.
    """
    agencies = Agency.objects.filter(status='active').values(
        'id', 'company_name'
    ).order_by('company_name')

    return JsonResponse({'agencies': list(agencies)})
