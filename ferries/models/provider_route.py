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


class RouteSchedule(models.Model):
    """
    Defines exactly WHICH days a route is available.
    Used to populate the available dates in your frontend calendar.
    """
    route = models.ForeignKey(
        ProviderRoute,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    date = models.DateField(db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'ferries_route_schedule'
        unique_together = ('route', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.route} | {self.date}"


class RoutePriceComponent(models.Model):
    """
    Atomic pricing for individual items.
    Example: Price for 1 Adult, Price for 1 Car, Price for 1 Cabin.
    """
    COMPONENT_TYPES = (
        ('pax', 'Passenger'),
        ('vehicle', 'Vehicle'),
        ('accommodation', 'Installation'),
    )

    route = models.ForeignKey(
        ProviderRoute,
        on_delete=models.CASCADE,
        related_name='price_components'
    )

    # Seasonality
    start_date = models.DateField()
    end_date = models.DateField()

    # Classification
    category = models.CharField(max_length=20, choices=COMPONENT_TYPES)

    # item_name MUST match your frontend 'type' (e.g., 'adult', 'child', 'standard_car', 'cabin')
    item_name = models.CharField(max_length=100)

    # Pricing
    net_price = models.DecimalField(
        max_digits=15, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(
        max_digits=15, decimal_places=2, default=0.00)

    class Meta:
        db_table = 'ferries_price_component'
        indexes = [
            models.Index(fields=['route', 'category', 'item_name']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['route', 'category', 'item_name'],
                name='unique_price_component_per_route'
            )
        ]

    def __str__(self):
        return f"{self.item_name} on {self.route.provider.code} ({self.selling_price} DA)"
