import random
import string
from django.db import models
from .provider_route import ProviderRoute


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
    voucher = models.FileField(upload_to='vouchers/', null=True, blank=True)

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
