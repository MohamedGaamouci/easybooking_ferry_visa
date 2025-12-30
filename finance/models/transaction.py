from django.db import models


class Transaction(models.Model):
    TYPES = (
        ('deposit', 'Deposit (TopUp)'),       # Money In
        ('payment', 'Payment (Invoice)'),     # Money Out
        ('refund', 'Refund'),                 # Money Back
        ('adjustment', 'Manual Adjustment'),  # Correction
    )

    # 1. Links
    account = models.ForeignKey(
        'finance.Account',
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    # Optional links to explain the money movement
    invoice = models.ForeignKey(
        'finance.Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    top_up = models.ForeignKey(
        'finance.TopUpRequest', on_delete=models.SET_NULL, null=True, blank=True)

    # 2. Money Details
    transaction_type = models.CharField(max_length=20, choices=TYPES)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Amount moved")
    balance_after = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Balance snapshot")

    description = models.CharField(max_length=255)

    # 3. Audit (Who did this?)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,  # If user is deleted, keep the record but set user to NULL
        null=True,
        blank=True,
        related_name='performed_transactions'
    )

    class Meta:
        db_table = 'finance_transaction'
        ordering = ['-created_at']  # Show newest first

    def __str__(self):
        return f"{self.transaction_type}: {self.amount} ({self.created_at.date()})"
