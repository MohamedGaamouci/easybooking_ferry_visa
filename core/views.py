from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.shortcuts import render
from visas.models import VisaDestination
from ferries.models import Port, Provider
# Include your Ferry Provider model import here if needed


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
