from django.db import models
from django.conf import settings
from .agency_tag import AgencyTag


class Agency(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    )

    # Basic Info
    company_name = models.CharField(max_length=100)

    # The Main Manager (One specific user who owns this account)
    manager = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='managed_agency'
    )

    # Contact & Legal
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=50)
    logo = models.ImageField(upload_to='agency_logos/', null=True, blank=True)

    rc_number = models.CharField(
        max_length=50, unique=True, verbose_name="Trade Registry")
    rc_document = models.FileField(
        upload_to='legal_docs/', null=True, blank=True)

    # Wallet / Finance
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00)
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    tags = models.ManyToManyField(AgencyTag, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'agencies_agency'

    def __str__(self):
        return self.company_name

    @property
    def tags_list(self):
        return self.tags.all()
