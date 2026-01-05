from django.urls import path
from ..views import *


urlpatterns = [

    path("visas/", visa_list_view, name="admin_visa_app"),
    path("api/visa/<int:app_id>/",
         get_visa_details, name="api_visa_details"),
    path("api/visa/update/",
         update_visa_application, name="api_visa_update"),
    # In your patterns:
    path("api/visa/destinations/",
         get_visa_destinations_api, name="api_visa_destinations"),
    # 2. CREATE (The Missing Link) - Add this line
    path("visas/create/", visa_create_view,
         name="visa_create"),  # <--- Here
    path("api/visa/schema/<int:destination_id>/",
         get_visa_schema, name="api_visa_schema"),
    path('visas/new-destination',
         visa_destination_create_view, name='visa_destination_create'),
    # 2. GET DETAILS (For Edit Modal)
    path('api/visa/destination/<int:pk>/', visa_destination_detail_api,
         name='api_visa_destination_detail'),

    # 3. UPDATE (For Saving Edits)
    path('api/visa/update_destination/<int:pk>/',
         visa_destination_update_view, name='visa_destination_update'),


]
