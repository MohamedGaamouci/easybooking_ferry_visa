from django.contrib import admin
from .models import (
    VisaDestination, VisaRequiredDocument,
    VisaForm, VisaFormField,
    VisaApplication, VisaApplicationDocument, VisaApplicationAnswer
)

# --- 1. Product Configuration ---


class RequiredDocumentInline(admin.TabularInline):
    model = VisaRequiredDocument
    extra = 1


@admin.register(VisaDestination)
class VisaDestinationAdmin(admin.ModelAdmin):
    list_display = ('country', 'visa_type', 'net_price',
                    'selling_price', 'is_active')
    search_fields = ('country',)
    list_filter = ('is_active',)
    # Add docs directly inside the Destination
    inlines = [RequiredDocumentInline]


class FormFieldInline(admin.TabularInline):
    model = VisaFormField
    extra = 1
    ordering = ['order_index']


@admin.register(VisaForm)
class VisaFormAdmin(admin.ModelAdmin):
    list_display = ('destination', 'version', 'is_active')
    inlines = [FormFieldInline]  # Add questions directly inside the Form

# --- 2. Applications (Client Data) ---


class ApplicationAnswerInline(admin.TabularInline):
    model = VisaApplicationAnswer
    extra = 0
    # readonly_fields = ('field',)


class ApplicationDocumentInline(admin.TabularInline):
    model = VisaApplicationDocument
    extra = 0
    # readonly_fields = ('file',)  # Safety: Don't change files, just view them


@admin.register(VisaApplication)
class VisaApplicationAdmin(admin.ModelAdmin):
    list_display = ('reference', 'agency', 'destination',
                    'last_name', 'status', 'created_at')
    list_filter = ('status', 'destination')
    search_fields = ('reference', 'last_name', 'passport_number')
    inlines = [ApplicationDocumentInline, ApplicationAnswerInline]
