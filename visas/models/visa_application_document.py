from django.db import models
from .visa_application import VisaApplication
from .visa_required_document import VisaRequiredDocument


class VisaApplicationDocument(models.Model):
    application = models.ForeignKey(
        VisaApplication,
        on_delete=models.CASCADE,
        related_name='uploaded_documents'
    )

    required_doc = models.ForeignKey(
        VisaRequiredDocument,
        on_delete=models.PROTECT
    )

    file = models.FileField(upload_to='visa_uploads/')

    # Logic: Admin can reject just ONE photo if it's blurry
    status = models.CharField(
        max_length=20,
        choices=(('pending', 'Pending'), ('valid', 'Valid'),
                 ('rejected', 'Rejected')),
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'visas_application_document'
