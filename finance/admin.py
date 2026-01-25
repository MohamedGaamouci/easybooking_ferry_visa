from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html

from finance.models.CreditLimitHistory import CreditLimitHistory
from .models import Account, TopUpRequest, Invoice, InvoiceItem, Transaction
from .services.topup import approve_topup_request, reject_topup_request
from .services.invoice import pay_invoice

# =========================================================
# INLINE ITEMS (For Invoice View)
# =========================================================


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    # readonly_fields = ('amount', 'description')  # Prevent accidental edits


# =========================================================
# 1. ACCOUNT ADMIN (The Financial Overview)
# =========================================================
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('agency', 'balance_display', 'credit_limit',
                    'unpaid_hold', 'buying_power_display', 'updated_at')
    search_fields = ('agency__company_name',)
    readonly_fields = ('updated_at',)

    # Display Balance (Gate 2)
    def balance_display(self, obj):
        color = "green" if obj.balance >= 0 else "red"
        return format_html('<span style="color: {}; font-weight: bold;">{} DZD</span>', color, obj.balance)
    balance_display.short_description = "Cash Balance"

    # Display Buying Power (Gate 1)
    def buying_power_display(self, obj):
        # We access the property .buying_power defined in the model
        val = obj.buying_power
        color = "blue" if val > 0 else "red"
        return format_html('<span style="color: {};">{} DZD</span>', color, val)
    buying_power_display.short_description = "Buying Power"


# =========================================================
# 2. TOP-UP REQUEST ADMIN (Approvals)
# =========================================================
@admin.register(TopUpRequest)
class TopUpRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_agency', 'amount',
                    'reference_number', 'status_badge', 'created_at')
    list_filter = ('status',)
    search_fields = ('account__agency__company_name', 'reference_number')
    readonly_fields = ('reviewed_by', 'created_at')
    actions = ['action_approve', 'action_reject']

    def get_agency(self, obj):
        return obj.account.agency.company_name
    get_agency.short_description = "Agency"

    def status_badge(self, obj):
        colors = {'pending': 'orange', 'approved': 'green', 'rejected': 'red'}
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 4px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.status.upper()
        )
    status_badge.short_description = "Status"

    # --- ACTION: APPROVE ---
    def action_approve(self, request, queryset):
        count = 0
        for topup in queryset:
            if topup.status == 'pending':
                approve_topup_request(topup.id, request.user)
                count += 1
        self.message_user(
            request, f"{count} Request(s) Approved & Funds Added.", messages.SUCCESS)
    action_approve.short_description = "Approve Selected Requests"

    # --- ACTION: REJECT ---
    def action_reject(self, request, queryset):
        for topup in queryset:
            if topup.status == 'pending':
                reject_topup_request(topup.id, request.user,
                                     reason="Rejected via Admin Panel")
        self.message_user(
            request, "Selected requests rejected.", messages.WARNING)
    action_reject.short_description = "Reject Selected Requests"


# =========================================================
# 3. INVOICE ADMIN (Settlements)
# =========================================================
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'agency', 'total_amount',
                    'status_badge', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('invoice_number', 'agency__company_name')
    inlines = [InvoiceItemInline]
    actions = ['action_pay_system']

    def status_badge(self, obj):
        colors = {'unpaid': 'red', 'paid': 'green',
                  'cancelled': 'gray', 'refunded': 'blue'}
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, 'black'),
            obj.status.upper()
        )
    status_badge.short_description = "Status"

    # --- ACTION: MANUAL PAY (Uses Gate 2 Logic) ---
    def action_pay_system(self, request, queryset):
        success_count = 0
        fail_count = 0

        for invoice in queryset:
            if invoice.status == 'unpaid':
                try:
                    # Call the service we wrote
                    success, msg = pay_invoice(invoice.id, request.user)
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception:
                    fail_count += 1

        if success_count:
            self.message_user(
                request, f"{success_count} Invoices Paid Successfully.", messages.SUCCESS)
        if fail_count:
            self.message_user(
                request, f"{fail_count} Invoices Failed (Insufficient Funds or Error).", messages.ERROR)

    action_pay_system.short_description = "Attempt to Pay with Wallet Balance"


# =========================================================
# 4. TRANSACTION LEDGER
# =========================================================
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'agency_name',
                    'type_colored', 'amount', 'balance_after')
    list_filter = ('transaction_type',)
    search_fields = ('account__agency__company_name',
                     'description', 'invoice__invoice_number')

    def agency_name(self, obj):
        return obj.account.agency.company_name

    def type_colored(self, obj):
        color = "green" if obj.amount > 0 else "red"
        return format_html('<span style="color: {};">{}</span>', color, obj.get_transaction_type_display())
    type_colored.short_description = "Type"


@admin.register(CreditLimitHistory)
class CreditLimitHistoryAdmin(admin.ModelAdmin):
    # What columns to show in the list
    list_display = ('account', 'old_limit', 'new_limit',
                    'changed_by', 'created_at')

    # Add filters for easier searching
    list_filter = ('created_at', 'changed_by')

    # Make everything read-only so the history remains "True"
    readonly_fields = ('account', 'old_limit', 'new_limit',
                       'changed_by', 'created_at')

    # Search by agency name or reference
    search_fields = ('account__agency__name', 'reason')
