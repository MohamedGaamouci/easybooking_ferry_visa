from django.urls import path
from .views import *

urlpatterns = [
    path('agencies/', agency_management_view, name='agency_management'),
    path('api/agency/create/', agency_create_api, name='agency_create'),
    path('api/agency/update/<int:pk>/', agency_update_api, name='agency_update'),

]
