from django.urls import path
from ..views import *


urlpatterns = [
    # The Page

    path('', ferries_view, name='ferries'),
    path('new_ferry/', new_demand_view, name='new_ferry'),

    # The APIs
    path('api/demand/list/', get_client_requests_api, name='api_ferry_list'),
    path('api/provider/<int:provider_id>/routes/',
         get_provider_routes_api, name='api_provider_routes'),
    path('api/demand/create/', create_ferry_request_api, name='api_create_demand'),
    path('api/demand/update/<str:reference>/',
         update_ferry_request_api, name='api_update_demand'),
    path('api/demand/detail/<str:reference>/',
         get_ferry_request_detail_api, name='api_demand_detail'),
    path('api/demand/respond/<str:reference>/',
         respond_to_offer_api, name='api_demand_respond'),


    # Scheduling & Pricing Discovery
    path('api/route/<int:route_id>/available-dates/',
         get_available_dates_api, name='api_available_dates'),
    path('api/pricing/calculate/', validate_and_calculate_price_api,
         name='api_calculate_price'),
    path('api/route/<int:route_id>/options/',
         get_route_options_api, name='api_route_options'),
    # 1st Endpoint: List Prices
    path('api/admin/route/<int:route_id>/pricing/',
         get_route_pricing_api, name='api_get_pricing_client'),

]
