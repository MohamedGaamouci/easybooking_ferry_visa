from django.contrib import admin
from .models import Account, TopUpRequest, Invoice, InvoiceItem, Transaction


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('agency', 'balance', 'credit_limit', 'updated_at')
    search_fields = ('agency__company_name',)


@admin.register(TopUpRequest)
class TopUpRequestAdmin(admin.ModelAdmin):
    list_display = ('account', 'amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('agency__company_name', 'reference_number')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'agency',
                    'total_amount', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('invoice_number', 'agency__company_name')
    # This lets you add items directly inside the Invoice screen
    inlines = [InvoiceItemInline]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'agency_name',
                    'transaction_type', 'amount', 'balance_after')
    list_filter = ('transaction_type',)

    def agency_name(self, obj):
        return obj.account.agency.company_name
