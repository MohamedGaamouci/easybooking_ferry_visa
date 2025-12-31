from django.db import models
from .visa_form import VisaForm


class VisaFormField(models.Model):
    FIELD_TYPES = (
        ('text', 'Text Input'),
        ('number', 'Number Input'),
        ('date', 'Date Picker'),
        ('select', 'Dropdown Select'),
        ('checkbox', 'Checkbox (Yes/No)'),
    )

    form = models.ForeignKey(
        VisaForm,
        on_delete=models.CASCADE,
        related_name='fields'
    )

    label = models.CharField(
        max_length=255, help_text="Question text e.g. 'Mother's Name'")
    # field_key = models.CharField(
    #     max_length=50, help_text="Unique key for code e.g. 'mother_name'")
    field_type = models.CharField(
        max_length=20, choices=FIELD_TYPES, default='text')

    # If type is 'select', we store options here like: "Single,Married,Divorced"
    options = models.TextField(
        blank=True, null=True, help_text="Comma-separated options for dropdowns")

    is_required = models.BooleanField(default=True)
    order_index = models.IntegerField(
        default=0, help_text="Order to display in the form")

    class Meta:
        db_table = 'visas_form_field'
        ordering = ['order_index']

    def __str__(self):
        return f"{self.label} ({self.field_type})"
