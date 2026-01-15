from django.urls import path
from ..views import *

urlpatterns = [
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


    # --- ADMIN PAGES ---
    path('requests/', admin_requests_view, name='ferries_requests'),
    path('requests/process/<str:reference>/',
         admin_process_view, name='admin_process'),

    # --- ADMIN APIS ---
    path('api/requests/list/', get_admin_requests_api, name='api_admin_list'),
    path('api/requests/offer/<str:reference>/',
         admin_send_offer_api, name='api_admin_offer'),

    path('api/request/reject/<int:pk>/',
         admin_reject_request, name='api_reject_offer'),

    path('api/attach-voucher/', api_attach_voucher, name='api_attach_voucher'),
]
