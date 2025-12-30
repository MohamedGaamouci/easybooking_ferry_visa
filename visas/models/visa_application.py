import random
import string
from django.db import models
from .visa_destination import VisaDestination


def generate_visa_ref():
    suffix = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=6))
    return f"VS-{suffix}"


class VisaApplication(models.Model):
    STATUS_CHOICES = (
        ('new', 'New Application'),
        ('review', 'Under Review'),
        ('embassy', 'Submitted to Embassy'),
        ('ready', 'Ready for Collection'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    )

    reference = models.CharField(
        max_length=12, unique=True, db_index=True,
        default=generate_visa_ref, editable=False
    )

    agency = models.ForeignKey(
        'agencies.Agency',
        on_delete=models.CASCADE,
        related_name='visa_applications'
    )

    destination = models.ForeignKey(
        VisaDestination,
        on_delete=models.PROTECT,
        related_name='applications'
    )

    # Applicant Info (Basic info we always need, separate from dynamic fields)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    passport_number = models.CharField(max_length=50)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='new')

    # Admin Notes
    embassy_appointment_date = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'visas_application'

    def __str__(self):
        return f"{self.reference} - {self.last_name}"
