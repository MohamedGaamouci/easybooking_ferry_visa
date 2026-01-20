from django.urls import path
from .views import *


urlpatterns = [
    path("cms/", cms_dashboard_view, name="admin_cms"),
    path("dashboard/", admin_dashboard, name="admin_dashboard"),
    path("", admin_dashboard, name="admin_dashboard"),
    path('api/kpis/', api_dashboard_kpis, name='api_kpis'),
    path('api/dashboard/analytics/', api_performance_chart,
         name='api_performance_chart'),



]
