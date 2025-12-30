from django.db import models
from .visa_application import VisaApplication
from .visa_form_field import VisaFormField


class VisaApplicationAnswer(models.Model):
    application = models.ForeignKey(
        VisaApplication,
        on_delete=models.CASCADE,
        related_name='answers'
    )

    field = models.ForeignKey(
        VisaFormField,
        on_delete=models.PROTECT
    )

    # We store everything as text.
    # If it's a date "2025-01-01", it's text.
    # If it's a number "50", it's text.
    value = models.TextField()

    class Meta:
        db_table = 'visas_application_answer'
