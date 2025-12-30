from django.db import models


class Provider(models.Model):
    """
    Ferry Companies (e.g., Balearia, Corsica Linea).
    """
    name = models.CharField(max_length=100, unique=True,
                            blank=False, null=False)
    code = models.CharField(max_length=10, unique=True,
                            help_text="Short code e.g. BAL")
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    # Using ImageField requires Pillow (which you installed)
    logo = models.ImageField(upload_to='providers/', null=True, blank=True)

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ferries_provider'

    def __str__(self):
        return self.name
