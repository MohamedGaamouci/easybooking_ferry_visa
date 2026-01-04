from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import os

from .models import (
    VisaDestination,
    VisaForm,
    VisaFormField,
    VisaRequiredDocument,
    VisaApplication,
    VisaApplicationAnswer,
    VisaApplicationDocument
)

# ==========================================
# 1. CONFIGURATION FORMS (Admin Setup)
# ==========================================


class VisaDestinationForm(forms.ModelForm):

    class Meta:
        model = VisaDestination
        fields = '__all__'

    def clean_net_price(self):
        price = self.cleaned_data.get('net_price')
        if price and price < 0:
            raise ValidationError(_("Net price cannot be negative."))
        return price

    def clean_selling_price(self):
        price = self.cleaned_data.get('selling_price')
        if price and price < 0:
            raise ValidationError(_("Selling price cannot be negative."))
        return price

    def clean(self):
        cleaned_data = super().clean()
        net = cleaned_data.get('net_price')
        selling = cleaned_data.get('selling_price')

        # Logic Check: Warning or Error if selling < net (You lose money)
        if net and selling and selling < net:
            # We add a warning to the specific field, but let it pass if you really want to lose money
            # Or enforce it strict:
            raise ValidationError(
                _("Selling price should not be lower than Net price."))
        return cleaned_data


class VisaFormForm(forms.ModelForm):
    class Meta:
        model = VisaForm
        fields = '__all__'


class VisaFormFieldForm(forms.ModelForm):
    class Meta:
        model = VisaFormField
        fields = '__all__'

    def clean(self):
        """
        Logic Validation: If field_type is 'select', 'options' MUST be filled.
        """
        cleaned_data = super().clean()
        f_type = cleaned_data.get('field_type')
        options = cleaned_data.get('options')

        if f_type == 'select' and not options:
            raise ValidationError({
                'options': _("Options are required when Field Type is 'Dropdown Select'.")
            })
        return cleaned_data


class VisaRequiredDocumentForm(forms.ModelForm):
    class Meta:
        model = VisaRequiredDocument
        fields = '__all__'


# ==========================================
# 2. APPLICATION FORMS (Client/Agent Input)
# ==========================================

class VisaApplicationForm(forms.ModelForm):
    """
    Used for Creating/Initiating the Application.
    """
    class Meta:
        model = VisaApplication
        fields = ['agency', 'destination', 'first_name',
                  'last_name', 'passport_number', 'status']

    # def clean_passport_number(self):
    #     # Security/Consistency: Force Uppercase & Trim
    #     passport = self.cleaned_data.get('passport_number')
    #     if passport:
    #         # Alphanumeric check (optional, depending on country)
    #         if not passport.isalnum():
    #             raise ValidationError(
    #                 _("Passport number should contain only letters and numbers."))
    #         return passport.strip().upper()
    #     return passport

    def clean_destination(self):
        # Integrity: Cannot apply for an inactive destination
        destination = self.cleaned_data.get('destination')
        if destination and not destination.is_active:
            raise ValidationError(
                _("This destination is currently not accepting applications."))
        return destination


class UpdateVisaStatusForm(forms.ModelForm):
    """
    Used for Admin moving the status (Kanban).
    """
    class Meta:
        model = VisaApplication
        fields = ['status', 'admin_notes', 'embassy_appointment_date']

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        appt_date = cleaned_data.get('embassy_appointment_date')

        # Logic: If status is 'appointment', Date is MANDATORY
        if status == 'appointment' and not appt_date:
            raise ValidationError({
                'embassy_appointment_date': _("Appointment Date is required when status is 'Appointment Scheduled'.")
            })
        return cleaned_data


# ==========================================
# 3. DYNAMIC DATA FORMS (Submissions)
# ==========================================

class VisaApplicationAnswerForm(forms.ModelForm):
    """
    Validates a single dynamic answer.
    """
    class Meta:
        model = VisaApplicationAnswer
        fields = '__all__'

    def clean_value(self):
        # Basic sanitization to prevent script injection in text fields
        value = self.cleaned_data.get('value')
        if value:
            return value.strip()
        return value


class VisaApplicationDocumentForm(forms.ModelForm):
    """
    Validates file uploads (Size, Type, Extension).
    """
    class Meta:
        model = VisaApplicationDocument
        fields = '__all__'

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')

        if uploaded_file:
            # 1. Size Validation (Limit to 5MB)
            limit_mb = 5
            if uploaded_file.size > limit_mb * 1024 * 1024:
                raise ValidationError(
                    _(f"File too large. Size should not exceed {limit_mb} MB."))

            # 2. Extension Validation (Allow PDF, JPG, PNG)
            ext = os.path.splitext(uploaded_file.name)[1].lower()
            valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            if ext not in valid_extensions:
                raise ValidationError(
                    _("Unsupported file extension. Allowed: PDF, JPG, PNG."))

        return uploaded_file
