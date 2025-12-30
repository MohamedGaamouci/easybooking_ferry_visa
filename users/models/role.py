from django.db import models
from django.contrib.auth.models import Permission


class Role(models.Model):
    """
    Dynamic Roles.
    Example: 
    - Name: "Platform Worker"
    - Permissions: [Can view ferries, Can change visas] (Selected in Admin Panel)
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    # This is the magic line. It links a Role to specific actions.
    permissions = models.ManyToManyField(Permission, blank=True)

    class Meta:
        db_table = 'users_role'

    def __str__(self):
        return self.name
