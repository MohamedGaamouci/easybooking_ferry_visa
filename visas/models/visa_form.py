from django.db import models
from .visa_destination import VisaDestination


class VisaForm(models.Model):
    """
    Links a Destination to a set of Questions.
    We use 'version' so if you change the form later, old applications don't break.
    """
    destination = models.ForeignKey(
        VisaDestination,
        on_delete=models.CASCADE,
        related_name='forms'
    )
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'visas_form'

    def __str__(self):
        return f"Form for {self.destination} (v{self.version})"
