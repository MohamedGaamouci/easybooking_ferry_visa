from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from django.conf import settings


class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # 1. BYPASS: Static files, Media, and Default Django Admin
        if path.startswith(settings.STATIC_URL) or path.startswith(settings.MEDIA_URL) or path.startswith('/admin/'):
            return self.get_response(request)

        # 2. BYPASS: Anonymous users (login/signup) and Superusers (Owner)
        if not request.user.is_authenticated or request.user.is_superuser:
            return self.get_response(request)

        try:
            # Identify the URL name and current environment
            match = resolve(path)
            url_name = match.url_name
            is_admin_path = path.startswith('/admin_panel/')

            # 3. CRITICAL BYPASS: Don't block logout or the unauthorized page itself
            if url_name in ['unauthorized', 'logout', 'login']:
                return self.get_response(request)

        except Resolver404:
            return self.get_response(request)

        # 4. ENVIRONMENT GUARD (The Agency/Admin Split)
        # Logic for Admin Side (Agency is None)
        if request.user.agency is None:
            if not is_admin_path:
                return redirect('/admin_panel/dashboard/')

        # Logic for Agency Side (Agency is NOT None)
        else:
            if is_admin_path:
                return redirect('/dashboard/')

        # 5. DYNAMIC PERMISSION CHECK
        # This matches the 'access_url_name' pattern we built in the Roles view
        permission_codename = f"access_{url_name}"

        if not request.user.has_role_permission(permission_codename):
            # NEW: Redirect to your specialized unauthorized page
            return redirect('unauthorized')

        return self.get_response(request)
