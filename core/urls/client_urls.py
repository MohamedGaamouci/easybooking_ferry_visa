from django.urls import path
from core.views import api_agency_performance_chart, client_dashboard, api_agency_kpis, api_get_my_info


urlpatterns = [
    path("", client_dashboard, name="client_dashboard"),
    # path('api/kpis/', api_dashboard_kpis, name='api_kpis'),
    path('api/dashboard/analytics/', api_agency_performance_chart,
         name='api_agency_performance_chart'),
    path('api/agency/kpis/', api_agency_kpis, name='api_agency_kpis'),

    path('api/user/info/', api_get_my_info, name='api_user_info')
]
