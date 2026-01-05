from django.urls import path
from ..views import *

urlpatterns = [
    path("ferries/", admin_ferry_requests_view,
         name="admin_ferry_requests"),
    # Port Management
    path('api/ferry/port/create/',
         port_create_view, name='port_create'),
    path('api/ferry/port/<int:pk>/', port_detail_api,
         name='port_detail'),       # For Edit Modal (GET)
    path('api/ferry/port/update/<int:pk>/', port_update_view,
         name='port_update'),  # For Save (POST)

    # Provider Management (Unified Save View)
    path('api/ferry/provider/create/',
         provider_save_view, name='provider_create'),
    path('api/ferry/provider/update/<int:pk>/',
         provider_save_view, name='provider_update'),
    path('api/ferry/provider/<int:pk>/',
         provider_detail_api, name='provider_detail'),
]
