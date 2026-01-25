from django.db import models


class CreditLimitHistory(models.Model):
    account = models.ForeignKey(
        'finance.Account', on_delete=models.CASCADE, related_name='credit_history')
    old_limit = models.DecimalField(max_digits=12, decimal_places=2)
    new_limit = models.DecimalField(max_digits=12, decimal_places=2)
    changed_by = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Credit Limit History"
        ordering = ['-created_at']
