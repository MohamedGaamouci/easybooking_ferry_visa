from django.db import models
from django.contrib.auth.models import Permission


class Role(models.Model):
    # Define the two immutable bases
    ROLE_CATEGORIES = (
        ('ADMIN', 'Platform Admin Side'),
        ('AGENCY', 'Agency Client Side'),
    )

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    # NEW: This distinguishes the two sides of your platform
    category = models.CharField(
        max_length=10,
        choices=ROLE_CATEGORIES,
        default='AGENCY'
    )

    # Links a Role to specific actions (our access_url_name permissions)
    permissions = models.ManyToManyField(Permission, blank=True)

    class Meta:
        db_table = 'users_role'

    def __str__(self):
        # Useful for debugging to see: "Manager (ADMIN)"
        return f"{self.name} ({self.category})"
