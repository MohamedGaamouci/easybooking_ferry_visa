from django.db import models
from .provider import Provider
from .port import Port


class ProviderRoute(models.Model):
    """
    A specific route operated by a specific provider.
    Example: Balearia sailing from Algiers to Alicante.
    """
    provider = models.ForeignKey(
        Provider, on_delete=models.PROTECT, related_name='routes', null=False)

    origin = models.ForeignKey(
        Port, on_delete=models.PROTECT, related_name='departures', null=False)
    destination = models.ForeignKey(
        Port, on_delete=models.PROTECT, related_name='arrivals', null=False)

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'ferries_provider_route'
        # Ensure we don't duplicate the exact same route for the same provider
        unique_together = ('provider', 'origin', 'destination')

    def __str__(self):
        return f"{self.provider.code}: {self.origin.code} -> {self.destination.code}"
