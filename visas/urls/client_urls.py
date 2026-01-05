from django.urls import path
from ..views import *


urlpatterns = [
    # --- PAGES ---
    # Marketplace (List of Destinations)
    path('', visa_view, name='visa_marketplace'),

    # Application Form (e.g., /visas/apply/?destination_id=5)
    path('apply/', new_visa_view, name='new_visa_application'),

    # --- APIs (Used by JavaScript) ---

    # 1. Get Form Schema: Fields & Required Docs for a specific destination
    path('api/schema/<int:destination_id>/',
         get_visa_schema, name='api_visa_schema'),

    # 2. Submit Application: Receives the JSON data + Files
    path('api/create/', visa_create_view, name='api_visa_create'),

    # APIs
    path('api/list/', get_client_visa_destinations_api,
         name='api_visa_list'),  # For Grid
    path('api/detail/<int:pk>/', get_client_visa_detail_api,
         name='api_visa_detail'),  # For Drawer


    path('my-applications/', requests,
         name='visa_applications'),  # The Page
    path('api/my-applications/', get_client_applications_api,
         name='api_visa_applications'),  # The API

]
