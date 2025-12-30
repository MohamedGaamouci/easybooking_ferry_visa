from django.db import models


class AgencyTag(models.Model):
    """
    Tags for filtering: 'VIP', 'Wholesaler', 'Bad Payer'
    """
    name = models.CharField(max_length=50)
    color = models.CharField(
        max_length=20, default="blue", help_text="CSS color name or hex")

    class Meta:
        db_table = 'agencies_tag'

    def __str__(self):
        return self.name
