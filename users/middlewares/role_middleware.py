from django.shortcuts import redirect


class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Skip checks for anonymous users (login/signup) and superusers
        if not request.user.is_authenticated or request.user.is_superuser:
            return self.get_response(request)

        path = request.path
        is_admin_path = path.startswith('/admin_panel')

        # 2. Logic for Admin Side (Agency is None)
        if request.user.agency is None:
            # If an admin tries to access a non-admin path
            if not is_admin_path:
                # Redirect them to the admin dashboard (change 'admin_home' to your actual name)
                return redirect('/admin_panel/dashboard/')

        # 3. Logic for Agency Side (Agency is NOT None)
        else:
            # If an agency user tries to access any path starting with admin_panel
            if is_admin_path:
                # Redirect them back to the client/agency side
                return redirect('/')

        return self.get_response(request)
