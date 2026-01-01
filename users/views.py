from django.shortcuts import render
from django.contrib.auth import get_user_model
from agencies.models import Agency
from .models import Role  # Assuming Role is in the users app


def admin_users_view(request):
    """
    Renders the User Management page with users, agencies, and roles.
    """
    User = get_user_model()

    # 1. Fetch Users
    # Use select_related to fetch Agency and Role data in a single query (Optimization)
    users = User.objects.select_related(
        'agency', 'role').all().order_by('-date_joined')

    # 2. Fetch Filters Data
    agencies = Agency.objects.only('id', 'company_name').all()
    roles = Role.objects.all()

    context = {
        'users': users,
        'agencies': agencies,
        'roles': roles,
    }

    return render(request, 'admin/users.html', context)
