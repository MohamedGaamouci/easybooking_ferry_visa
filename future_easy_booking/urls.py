"""
URL configuration for future_easy_booking project.
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from agencies.views import admin_agencies_view, get_agencies_api
from users.views import admin_users_view
from visas.views import *
from core.views import *


# ======================
# Admin Views
# ======================

def admin_dashboard_view(request):
    return render(request, 'admin/dashboard.html')


def admin_setting_view(request):
    return render(request, 'admin/setting.html')


def admin_accounting_view(request):
    return render(request, 'admin/accounting.html')


def admin_ferry_requests_view(request):
    return render(request, 'admin/ferry_requests.html')


# ======================
# client Views
# ======================

def ferries_view(request):
    return render(request, 'client/ferry_requests.html')


def dashboard_view(request):
    return render(request, 'client/dashboard.html')


def accounting_view(request):
    return render(request, 'client/accounting.html')


def new_ferry_view(request):
    return render(request, 'client/new_ferry.html')


def new_visa_view(request):
    return render(request, 'client/new_visa.html')


def setting_view(request):
    return render(request, 'client/setting.html')


def visa_view(request):
    return render(request, 'client/visa.html')


# ======================
# URL Patterns
# ======================

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),
]

admin_urls = [
    # Custom Admin Panel
    path("admin_panel/dashboard/", admin_dashboard_view, name="admin_dashboard"),
    path("admin_panel/settings/", admin_setting_view, name="admin_setting"),
    path("admin_panel/accounting/", admin_accounting_view, name="admin_accounting"),



    path("admin_panel/agencies/", admin_agencies_view, name="admin_agencies"),
    path("admin_panel/api/agencies/", get_agencies_api,
         name="api_agencies"),  # <--- Add this



    path("admin_panel/users/", admin_users_view, name="admin_users"),
    path("admin_panel/cms/", cms_dashboard_view, name="admin_cms"),
    path("admin_panel/ferries/", admin_ferry_requests_view,
         name="admin_ferry_requests"),
    path("admin_panel/visas/", visa_list_view, name="admin_visa_app"),
    path("admin_panel/api/visa/<int:app_id>/",
         get_visa_details, name="api_visa_details"),
    path("admin_panel/api/visa/update/",
         update_visa_application, name="api_visa_update"),
    # In your patterns:
    path("admin_panel/api/visa/destinations/",
         get_visa_destinations_api, name="api_visa_destinations"),
    # 2. CREATE (The Missing Link) - Add this line
    path("admin_panel/visas/create/", visa_create_view,
         name="visa_create"),  # <--- Here
    path("admin_panel/api/visa/schema/<int:destination_id>/",
         get_visa_schema, name="api_visa_schema"),
    path('admin_panel/visas/new-destination',
         visa_destination_create_view, name='visa_destination_create'),
    # 2. GET DETAILS (For Edit Modal)
    path('admin_panel/api/visa/destination/<int:pk>/', visa_destination_detail_api,
         name='api_visa_destination_detail'),

    # 3. UPDATE (For Saving Edits)
    path('admin_panel/api/visa/update_destination/<int:pk>/',
         visa_destination_update_view, name='visa_destination_update'),
]
urlpatterns += admin_urls

client_urls = [
    path('ferries/', ferries_view, name='ferries'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('accounting/', accounting_view, name='accounting'),
    path('new_ferry/', new_ferry_view, name='new_ferry'),
    path('new_visa/', new_visa_view, name='new_visa'),
    path('setting/', setting_view, name='setting'),
    path('visa/', visa_view, name='visa'),
]
urlpatterns += client_urls

# ======================
# Static & Media
# ======================

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL,
                          document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
