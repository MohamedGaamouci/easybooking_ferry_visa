import random
import string
from django.db import models
from .visa_destination import VisaDestination
from finance.services.notifications import notify_new_request_received, notify_status_change


def generate_visa_ref():
    suffix = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=6))
    return f"VS-{suffix}"


class VisaApplication(models.Model):
    # --- Updated Status Workflow ---
    STATUS_CHOICES = (
        ('new', 'New Application'),                 # Step 1: Client submits
        ('review', 'Under Review'),                 # Step 2: Admin checks docs
        # Step 3: Date is booked (NEW)
        ('appointment', 'Appointment Scheduled'),
        # Step 4: File is at Consulate
        ('embassy', 'Submitted to Embassy'),
        ('ready', 'Ready for Collection'),          # Step 5: Passport is back
        # Step 6: Client picked it up
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),                   # Exception: Refused
        ('cancelled', 'Cancelled')
    )

    reference = models.CharField(
        max_length=12, unique=True, db_index=True,
        default=generate_visa_ref, editable=False
    )

    agency = models.ForeignKey(
        'agencies.Agency',
        on_delete=models.PROTECT,
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
    admin_notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    apply_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.PROTECT,
        related_name='apply_by',
        help_text="The user who apply the visa.",
        null=True,
        blank=True
    )

    user_admin = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.PROTECT,
        related_name='treated_by',
        help_text="The admin user who treat the application.",
        null=True,
        blank=True
    )

    visa_doc = models.FileField(
        upload_to='visa_uploads/ready/', blank=True, null=True)

    class Meta:
        db_table = 'visas_application'

    def __str__(self):
        return f"{self.reference} - {self.last_name}"

    def save(self, *args, **kwargs):
        # 1. Check if this is a new application or an update
        is_new = self._state.adding

        # 2. Capture old status for comparison
        old_status = None
        if not is_new:
            # Dynamically fetches the current record from DB
            old_instance = type(self).objects.get(pk=self.pk)
            old_status = old_instance.status

        # 3. Commit to database
        super().save(*args, **kwargs)

        # 4. Fire notifications
        try:
            if is_new:
                # Sends the "Reservation Received" email for Visa
                notify_new_request_received(self, Type="Visa")

            elif old_status != self.status:
                # Sends the "Status Update" email (e.g., New -> Under Review)
                notify_status_change(self, old_status)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Visa Notification Error [{self.reference}]: {e}")
