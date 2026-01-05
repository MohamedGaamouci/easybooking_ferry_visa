from django.urls import path
from ..views import *
from django.contrib.auth import views as auth_views
from .. import views


urlpatterns = [

    # 1. Login Page
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True
    ), name='login'),

    # 2. Logout Action
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # 3. Smart Router (Redirects based on Role)
    path('login-success/', views.login_success_router, name='login_success'),
]
