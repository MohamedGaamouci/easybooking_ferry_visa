
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

# 1. THE WALLET BALANCE
    # Positive = They have money.
    # Negative = They owe you money (if you allow it).
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Wallet Balance"
    )
# 2. CREDIT LIMIT (Overdraft)
    # If this is 50,000, the agency can spend until their balance is -50,000.
    # Set to 0 if they must prepay for everything.
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="Credit Limit"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'finance_account'

    def __str__(self):
        return f"{self.agency.company_name} ({self.balance} DZD)"
