from django.urls import path
from core.views import api_agency_performance_chart, client_dashboard, api_agency_kpis


urlpatterns = [
    path("", client_dashboard, name="client_dashboard"),
    # path('api/kpis/', api_dashboard_kpis, name='api_kpis'),
    path('api/dashboard/analytics/', api_agency_performance_chart,
         name='api_agency_performance_chart'),
    path('api/agency/kpis/', api_agency_kpis, name='api_agency_kpis'),
]
