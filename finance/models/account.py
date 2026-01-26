from crum import get_current_user
from django.db import models

from finance.models.CreditLimitHistory import CreditLimitHistory


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
        # return self.credit_limit - self.unpaid_hold
        return self.credit_limit

    def __str__(self):
        return f"{self.agency}: Cash {self.balance} | Avail Vol {self.buying_power}"

    def save(self, reason=None, *args, **kwargs):
        if self.pk:  # Only on update, not creation
            try:
                old_instance = Account.objects.get(pk=self.pk)
                if old_instance.credit_limit != self.credit_limit:
                    user = get_current_user()

                    # Create the history record
                    CreditLimitHistory.objects.create(
                        account=self,
                        old_limit=old_instance.credit_limit,
                        new_limit=self.credit_limit,
                        changed_by=user if user and not user.is_anonymous else None,
                        reason=reason
                    )
            except Account.DoesNotExist:
                pass

        super().save(*args, **kwargs)
