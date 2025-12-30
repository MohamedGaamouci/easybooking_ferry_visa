from django.db import models
from django.contrib.auth.models import AbstractUser
from .role import Role


class CustomUser(AbstractUser):
    # 1. Login Field
    email = models.EmailField(unique=True)

    # 2. Contact Info
    # Phone is okay to be unique if you want strict 1-number-per-user rules.
    phone = models.CharField(max_length=20, blank=False, unique=True)
    state = models.CharField(max_length=20, blank=False)

    updated_at = models.DateTimeField(auto_now=True)

    # 3. Relationships
    # Platform users have NO agency (Null). Agency users have an agency.
    agency = models.ForeignKey(
        'agencies.Agency',
        on_delete=models.SET_NULL,
        related_name='users',
        null=True,
        blank=True
    )

    role = models.ForeignKey(
        Role, on_delete=models.SET_NULL, null=True, blank=True)

    # 4. Configuration
    USERNAME_FIELD = 'email'

    # IMPORTANT: Fields required when running 'createsuperuser'
    # 'email' and 'password' are auto-required by Django.
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'phone', 'state']

    class Meta:
        db_table = 'users_customuser'

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Auto-logic: If user is Superuser (You), you don't need a role.
        if self.is_superuser:
            self.role = None
        super().save(*args, **kwargs)

    def has_role_permission(self, codename):
        """
        Check if the user's role allows a specific action.
        Usage: request.user.has_role_permission('view_finance')
        """
        if self.is_superuser:
            return True  # You can do anything

        if self.role and self.role.permissions.filter(codename=codename).exists():
            return True

        return False
