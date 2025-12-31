from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Role


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Columns to show in the list
    list_display = ('email', 'first_name', 'last_name',
                    'agency', 'role', 'phone', 'is_active')
    list_filter = ('agency', 'role', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('email',)

    # Configuration for the "Edit User" form
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name',
         'last_name', 'phone', 'state', 'address')}),
        ('Permissions', {
         'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Professional', {'fields': ('agency',)}),  # <--- Our custom field
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
