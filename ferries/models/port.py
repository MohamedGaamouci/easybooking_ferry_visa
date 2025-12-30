from django.db import models


class Port(models.Model):
    """
    Seaports (e.g., Algiers, Alicante, Marseille).
    """
    name = models.CharField(max_length=100, blank=False, null=False)
    code = models.CharField(max_length=5, unique=True,
                            help_text="Port Code e.g. ALG")
    city = models.CharField(max_length=100, blank=False, null=False)
    country = models.CharField(max_length=100, blank=False, null=False)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'ferries_port'

    def __str__(self):
        return f"{self.name} ({self.code})"
