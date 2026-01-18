from django.urls import path
from .views import *


urlpatterns = [
    path("cms/", cms_dashboard_view, name="admin_cms"),
    path("dashboard/", admin_dashboard, name="admin_dashboard"),
    path("", admin_dashboard, name="admin_dashboard"),


]
