"""
URL configuration for future_easy_booking project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
# ======================
# Admin Views
# ======================


def home(request):
    return render(request, 'admin/dashboard.html')


def admin_setting_view(request):
    return render(request, 'admin/setting.html')


# ======================
# client Views
# ======================

def client_home(request):
    return render(request, 'client/dashboard.html')


def dashboard_view(request):
    return render(request, 'client/dashboard.html')


def new_ferry_view(request):
    return render(request, 'client/new_ferry.html')


def new_visa_view(request):
    return render(request, 'client/new_visa.html')


def setting_view(request):
    return render(request, 'client/setting.html')


# ======================
# URL Patterns
# ======================

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

]

admin_urls = [
    # Custom Admin Panel
    path("admin_panel/", include('core.urls')),
    path("admin_panel/settings/", admin_setting_view, name="admin_setting"),


    #   AGENCIES
    path("admin_panel/", include('finance.urls.urls')),

    #   AGENCIES
    path("admin_panel/", include('agencies.urls')),

    #   USERS
    path('admin_panel/', include('users.urls.urls')),

    #   CMS
    path('admin_panel/', include('core.urls')),

    #   FERRY URLS
    path('admin_panel/', include('ferries.urls.urls')),

    #   VISA URLS
    path('admin_panel/', include('visas.urls.urls'))

]
urlpatterns += admin_urls

client_urls = [
    path('', client_home, name='dashboard'),
    path('ferries/', include('ferries.urls.client_urls')),
    path('users/', include('users.urls.client_urls')),
    path('visas/', include('visas.urls.client_urls')),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('accounting/', include('finance.urls.client_urls')),
    path('setting/', setting_view, name='setting'),
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
