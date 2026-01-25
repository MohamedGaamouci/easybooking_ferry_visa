import random
import string
from django.db import models
from .provider_route import ProviderRoute
from finance.services.notifications import notify_status_change, notify_new_request_received


def generate_reference():
    """Generates a random unique code like 'FER-93821'."""
    # Simple logic: 'FER-' + 6 random digits/letters.
    # You can make this more complex if needed.
    suffix = ''.join(random.choices(
        string.ascii_uppercase + string.digits, k=6))
    return f"FER-{suffix}"


class FerryRequest(models.Model):
    # --- Status Logic (Single Source of Truth) ---
    STATUS_CHOICES = (
        ('pending', 'Pending'),           # Admin: New | Client: Pending
        # Admin: Processing | Client: Processing
        ('processing', 'Processing'),
        # Admin: Waiting Confirm | Client: Offer Received
        ('offer_sent', 'Offer Sent'),
        ('confirmed', 'Confirmed'),       # Both: Confirmed
        ('cancelled', 'Cancelled'),       # Both: Cancelled
        ('rejected', 'Rejected'),         # Both: Rejected
    )

    TRIP_TYPES = (
        ('round', 'Round Trip'),
        ('oneway', 'One Way'),
    )

    # 1. Identity
    # unique=True: Ensures no duplicates.
    # db_index=True: Makes searching super fast (SELECT * WHERE reference = '...')
    # default=generate_reference: Auto-creates the code on new requests.
    reference = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        default=generate_reference,
        editable=False
    )

    # 2. Links
    agency = models.ForeignKey(
        'agencies.Agency',
        on_delete=models.PROTECT,
        related_name='ferry_requests',
        null=False
    )

    # PROTECT is perfect here. You can't delete a Route if people have booked it.
    route = models.ForeignKey(
        ProviderRoute,
        on_delete=models.PROTECT,
        # Renamed from 'route' to 'requests' for clarity (route.requests.all())
        related_name='requests',
        null=False
    )

    # 3. Trip Details
    trip_type = models.CharField(
        max_length=10, choices=TRIP_TYPES, default='round', null=False)

    departure_date = models.DateField(null=False, blank=False)
    return_date = models.DateField(null=True, blank=True)

    # 4. Dynamic Data
    passengers_data = models.JSONField(default=dict, null=False, blank=False)
    vehicle_data = models.JSONField(default=dict, null=True, blank=True)

    accommodation = models.CharField(
        max_length=50, default="Seat", help_text="Seat, Cabin, etc.")

    # 5. Finance
    net_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, blank=True, default=0.00)
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, blank=True, default=0.00)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')

    # 6. Documents
    voucher = models.FileField(
        upload_to='ferry/vouchers/', null=True, blank=True)

    user_admin = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.PROTECT,
        related_name="admin_user",
        help_text="The administrator user responsible for managing this record.",
        blank=True,
        null=True
    )

    requested_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.PROTECT,
        related_name="requested_by",
        help_text="User who submitted the request for this record.",
        blank=True,
        null=True
    )

    admin_note = models.TextField(
        null=True, blank=True, help_text="notes from the admin to the agency")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # breakdown is stored to keep a record of prices at time of booking
    price_breakdown = models.JSONField(null=True)

    class Meta:
        db_table = 'ferries_request'

    def __str__(self):
        return f"{self.reference} ({self.agency})"

    # --- UI Helpers (The "Magic" for your Labels) ---

    @property
    def client_status_label(self):
        """What the Client sees"""
        labels = {
            'pending': 'Pending',
            'processing': 'In Progress',
            'offer_sent': 'Action Required: Offer Received',
            'confirmed': 'Confirmed',
            'cancelled': 'Cancelled',
            'rejected': 'Rejected'
        }
        return labels.get(self.status, self.status)

    @property
    def admin_status_label(self):
        """What the Admin sees"""
        labels = {
            'pending': 'New Request',
            'processing': 'Processing',
            'offer_sent': 'Waiting Client Confirmation',
            'confirmed': 'Confirmed',
            'cancelled': 'Cancelled',
            'rejected': 'Rejected'
        }
        return labels.get(self.status, self.status)

    def save(self, *args, **kwargs):
        # 1. Identify if this is a new creation or an edit
        is_new = self._state.adding

        # 2. Capture the current status from the DB before overwriting it
        old_status = None
        if not is_new:
            # We use type(self) to make this snippet reusable across different models
            old_instance = type(self).objects.get(pk=self.pk)
            old_status = old_instance.status

        # 3. Commit the changes to the database
        super().save(*args, **kwargs)

        # 4. Handle Notifications with a safety net
        try:
            # Local imports prevent circular dependency errors in Django

            if is_new:
                # Triggers the "Reservation Received" email
                notify_new_request_received(self)

            elif old_status != self.status:
                # Triggers the "Status Update" email
                notify_status_change(self, old_status)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Notification error for {self.reference}: {e}")
