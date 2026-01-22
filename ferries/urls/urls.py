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


    # Admin Management
    path('api/admin/route/<int:route_id>/schedule/',
         admin_manage_schedule_api, name='admin_manage_schedule'),
    path('api/admin/route/<int:route_id>/pricing/save/',
         admin_save_price_component_api, name='admin_save_pricing'),
    # 1st Endpoint: List Prices
    path('api/admin/route/<int:route_id>/pricing/',
         get_route_pricing_api, name='api_get_pricing'),

    # 3rd Endpoint: Delete Price
    path('api/admin/pricing/delete/<int:component_id>/',
         delete_price_component_api, name='api_delete_pricing'),
    # Admin Schedule Management
    path('api/admin/route/<int:route_id>/calendar/',
         get_admin_route_calendar_api, name='api_admin_route_calendar'),
    path('api/admin/schedule/delete/<int:schedule_id>/',
         delete_schedule_date_api, name='api_delete_schedule_date'),
    #     pricing/structure/
    path('/api/pricing/structure/',
         get_pricing_structure_api, name='api_pricing_structure'),
]
