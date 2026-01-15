from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Role


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # Columns to show in the list
    list_display = (
        'email', 'username', 'first_name', 'last_name',
        'agency', 'role', 'phone', 'is_active'
    )
    list_filter = ('agency', 'role', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('email',)

    # Configuration for the "Edit User" form
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone', 'state')
        }),
        ('Professional', {
            'fields': ('agency', 'role')
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'password1',
                'password2',
                'first_name',
                'last_name',
                'phone',
                'state',
                'agency',
                'role',
                'is_staff',
                'is_superuser',
            ),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
