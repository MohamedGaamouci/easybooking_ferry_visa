
from django.db import models


class Account(models.Model):
    """
    The Single Main Wallet for the Agency.
    """
    agency = models.OneToOneField(  # Changed from ForeignKey to OneToOne
        'agencies.Agency',
        on_delete=models.CASCADE,
        related_name='account'
    )

    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00)

    # Optional: If you want to allow them to go negative (Credit)
    overdraft_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_account'

    def __str__(self):
        return f"{self.agency.company_name} ({self.balance} DZD)"
