from django.urls import path
from .views import cms_dashboard_view


urlpatterns = [
    path("cms/", cms_dashboard_view, name="admin_cms"),

]
