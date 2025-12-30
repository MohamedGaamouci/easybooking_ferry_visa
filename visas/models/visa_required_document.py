from django.db import models
from .visa_destination import VisaDestination


class VisaRequiredDocument(models.Model):
    """
    Defines what files the user MUST upload.
    e.g. 'Passport Scan', 'Photo 5x5', 'Bank Statement'
    """
    destination = models.ForeignKey(
        VisaDestination,
        on_delete=models.CASCADE,
        related_name='required_documents'
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)

    class Meta:
        db_table = 'visas_required_document'

    def __str__(self):
        return self.name
