from django.db import models


class Account(models.Model):
    agency = models.OneToOneField(
        'agencies.Agency',
        on_delete=models.CASCADE,
        related_name='account'
    )

    # GATE 2: SETTLEMENT FUNDS (Real Cash)
    # Used ONLY to pay invoices. Cannot go negative.
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Cash Balance"
    )

    # GATE 1: PURCHASING LIMITS
    # The maximum volume of unpaid invoices allowed at once.
    credit_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Credit Line"
    )

    # CONSUMED VOLUME
    # Sum of all currently UNPAID invoices.
    unpaid_hold = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00
    )

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def buying_power(self):
        """
        STRICT MODE:
        Purchasing Power comes ONLY from the Credit Line.
        Formula: Credit Limit - Used Hold.
        (Balance is ignored here).
        """
        return self.credit_limit - self.unpaid_hold

    def __str__(self):
        return f"{self.agency}: Cash {self.balance} | Avail Vol {self.buying_power}"
