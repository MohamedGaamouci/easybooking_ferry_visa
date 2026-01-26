"""
URL configuration for future_easy_booking project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.views.generic import RedirectView
# ======================
# Admin Views
# ======================


def admin_setting_view(request):
    return render(request, 'admin/setting.html')


# ======================
# client Views
# ======================

def setting_view(request):
    return render(request, 'client/setting.html')

# ======================
# 403 page
# ======================


def unauthorized_view(request):
    return render(request, 'errors/403.html', status=403)
# ======================
# URL Patterns
# ======================


urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url='dashboard/', permanent=False)),
    path('unauthorized/', unauthorized_view, name='unauthorized'),

]

admin_urls = [
    # Custom Admin Panel
    path("admin_panel/", include('core.urls.urls')),
    path("admin_panel/settings/", admin_setting_view, name="admin_setting"),


    #   AGENCIES
    path("admin_panel/", include('finance.urls.urls')),

    #   AGENCIES
    path("admin_panel/", include('agencies.urls')),

    #   USERS
    path('admin_panel/', include('users.urls.urls')),

    #   FERRY URLS
    path('admin_panel/', include('ferries.urls.urls')),

    #   VISA URLS
    path('admin_panel/', include('visas.urls.urls'))

]
urlpatterns += admin_urls

client_urls = [
    path("dashboard/", include('core.urls.client_urls')),
    path('ferries/', include('ferries.urls.client_urls')),
    path('users/', include('users.urls.client_urls')),
    path('visas/', include('visas.urls.client_urls')),
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
