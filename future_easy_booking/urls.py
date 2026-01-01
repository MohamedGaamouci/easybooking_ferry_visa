"""
URL configuration for future_easy_booking project.
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from agencies.views import admin_agencies_view


# ======================
# Admin Views
# ======================

def admin_dashboard_view(request):
    return render(request, 'admin/dashboard.html')


def admin_setting_view(request):
    return render(request, 'admin/setting.html')


def admin_accounting_view(request):
    return render(request, 'admin/accounting.html')


# def admin_agencies_view(request):
#     return render(request, 'admin/agencies.html')


def admin_users_view(request):
    return render(request, 'admin/users.html')


def admin_cms_view(request):
    return render(request, 'admin/cms.html')


def admin_ferry_requests_view(request):
    return render(request, 'admin/ferry_requests.html')


def admin_visa_app_view(request):
    return render(request, 'admin/visa_application.html')


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
    path("admin_panel/users/", admin_users_view, name="admin_users"),
    path("admin_panel/cms/", admin_cms_view, name="admin_cms"),
    path("admin_panel/ferries/", admin_ferry_requests_view,
         name="admin_ferry_requests"),
    path("admin_panel/visas/", admin_visa_app_view, name="admin_visa_app"),
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
