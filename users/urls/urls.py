from django.urls import path
from ..views import *
from django.contrib.auth import views as auth_views
from .. import views


urlpatterns = [

    path('users/', user_management_view, name='user_management'),
    path('api/user/<int:pk>/', user_detail_api, name='user_detail'),
    path('api/user/create/', user_save_view, name='user_create'),
    path('api/user/update/<int:pk>/', user_save_view, name='user_update'),

    # ROLES (Fixed)
    path('roles/', role_management_view, name='role_management'),
    path('api/role/create/', role_save_view,
         name='role_create'),          # <--- Added this
    path('api/role/update/<int:pk>/', role_save_view,
         name='role_update'),  # <--- Renamed this
    path('api/role/<int:pk>/', role_detail_api, name='role_detail'),


]
