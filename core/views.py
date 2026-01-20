from datetime import datetime

from django.http import JsonResponse

from agencies.models.agency import Agency
# Make sure KPI is imported from your services file
from .services import KPI, DashboardService
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.shortcuts import render
from visas.models import VisaDestination
from ferries.models import Port, Provider
from django.views.decorators.http import require_GET
# Include your Ferry Provider model import here if needed


@login_required
@require_GET
def cms_dashboard_view(request):
    # --- 1. VISA DESTINATIONS QUERY ---
    # We only need the destination fields, not the child objects yet.
    queryset = VisaDestination.objects.all().order_by('-created_at')

    # --- 2. FILTERING ---
    # Search (Visa Name, Country, Type)
    search_query = request.GET.get('q', '')
    if search_query:
        queryset = queryset.filter(
            Q(country__icontains=search_query) |
            Q(visa_name__icontains=search_query) |
            Q(visa_type__icontains=search_query)
        )

    # Status Filter (Active/Disabled)
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        queryset = queryset.filter(is_active=True)
    elif status_filter == 'disabled':
        queryset = queryset.filter(is_active=False)

    # --- 3. PAGINATION ---
    # Show 8 cards per page (Grid layout: 4 columns x 2 rows)
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page', 1)

    try:
        visa_destinations = paginator.page(page_number)
    except PageNotAnInteger:
        visa_destinations = paginator.page(1)
    except EmptyPage:
        visa_destinations = paginator.page(paginator.num_pages)

    # ferries
    # --- FERRY SECTION DATA ---
    ferry_providers = Provider.objects.all().order_by('name')
    ports = Port.objects.all().order_by('country', 'city')

    context = {
        'visa_destinations': visa_destinations,
        'search_query': search_query,   # To keep search box populated
        'status_filter': status_filter,  # To keep dropdown selected
        # 'ferry_providers': ... (Keep your existing ferry logic here)
        'ferry_providers': ferry_providers,
        'ports': ports,
    }

    return render(request, 'admin/cms.html', context)

# Your existing admin check


# core/views.py

def is_admin(user):
    # Ensure user is authenticated first
    if not user.is_authenticated:
        return False

    # In your logic, a Master Admin is a user WITHOUT an agency attached
    # We use 'hasattr' to safely check if the agency relation exists
    if hasattr(user, 'agency') and user.agency is not None:
        return False  # They are an agency, not Master Admin

    # If they are superuser or staff, they are definitely admin
    # Or if they simply don't have an agency attribute
    return user.is_staff or user.is_superuser or not hasattr(user, 'agency')


@user_passes_test(is_admin)
def admin_dashboard(request):
    """Returns only the static HTML shell."""
    return render(request, 'admin/dashboard.html')


@user_passes_test(is_admin)
def api_dashboard_kpis(request):
    """The JSON endpoint for Ajax."""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # 1. Date Conversion
    s_date = datetime.strptime(
        start_date, '%Y-%m-%d').date() if start_date else None
    e_date = datetime.strptime(
        end_date, '%Y-%m-%d').date() if end_date else None

    # 2. Initialize Services
    kpi_service = KPI()
    dashboard_service = DashboardService()

    # 3. Fetch KPI Data
    revenue = kpi_service.get_last_month_revenue(s_date, e_date)
    sales = kpi_service.get_sales_volume(s_date, e_date)
    pending = kpi_service.get_pending_counts()
    agencies = kpi_service.get_active_agencies_count(s_date, e_date)

    # 4. Fetch Dynamic Feed Data
    tasks = dashboard_service.get_urgent_tasks()
    wallet_health = dashboard_service.get_at_risk_agencies()  # New: Health

    return JsonResponse({
        # Revenue & Sales
        'revenue': float(revenue['total']),
        'paid': float(revenue['paid']),
        'unpaid': float(revenue['unpaid']),
        'sales_total': sales['total'],
        'ferry_count': sales['ferry'],
        'visa_count': sales['visa'],

        # Pending Status
        'pending_total': pending['total_pending'],
        'visa_pending': pending['visa_pending'],
        'ferry_pending': pending['ferry_pending'],

        # Agency Stats & Metadata
        'active_agencies': agencies['active_count'],
        'label': revenue['label'],

        # Dynamic Lists (Arrays)
        'tasks': tasks,
        'wallet_health': wallet_health,
    })


@user_passes_test(is_admin)
def api_performance_chart(request):
    """
    Dedicated endpoint for the Weekly/Date-Range Performance Chart.
    Query Params: start_date, end_date, agency_id (optional)
    """
    # 1. Parse Date Params
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    agency_id = request.GET.get('agency_id')

    s_date = datetime.strptime(
        start_date_str, '%Y-%m-%d').date() if start_date_str else None
    e_date = datetime.strptime(
        end_date_str, '%Y-%m-%d').date() if end_date_str else None

    # 2. Resolve Agency (if provided)
    agency = None
    if agency_id:
        try:
            agency = Agency.objects.get(id=agency_id)
        except Agency.DoesNotExist:
            pass

    # 3. Fetch Data from Service
    service = DashboardService()
    revenue_data = service.get_weekly_revenue_breakdown(
        s_date, e_date, agency=agency)
    volume_data = service.get_weekly_volume_breakdown(
        s_date, e_date, agency=agency)

    return JsonResponse({
        'status': 'success',
        'revenue_chart': revenue_data,
        'volume_chart': volume_data,
    })
