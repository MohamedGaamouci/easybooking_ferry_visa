from django.db import models


class TopUpRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    agency = models.ForeignKey('agencies.Agency', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    # Proof
    receipt_image = models.ImageField(upload_to='finance_receipts/')
    reference_number = models.CharField(
        max_length=50, blank=True, help_text="Bank Ref/CCP")

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'finance_top_up_request'
