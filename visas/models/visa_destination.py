from django.db import models


class VisaDestination(models.Model):
    """
    The Country or Visa Product. e.g. "France (Schengen)", "Turkey E-Visa".
    """
    country = models.CharField(max_length=100)
    visa_name = models.CharField(max_length=100, blank=True, null=True)

    visa_type = models.CharField(
        max_length=100, help_text="e.g. Tourist, Business")

    # Pricing
    net_price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Embassy Price")
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, help_text="Selling Price")

    # Info
    processing_time = models.CharField(
        max_length=50, help_text="e.g. 15-20 Days")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Image for the Catalog
    cover_image = models.ImageField(
        upload_to='visa_destinations/', null=True, blank=True)

    class Meta:
        db_table = 'visas_destination'

    def __str__(self):
        return f"{self.country} - {self.visa_type}"
