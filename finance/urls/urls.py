from django.urls import path
from .. import views_admin

urlpatterns = [
    path('accounting/', views_admin.admin_accounting_dashboard,
         name='admin_accounting'),
    path('api/ledger/', views_admin.admin_ledger_api, name='admin_ledger_api'),
    path('api/topup/<int:topup_id>/process/',
         views_admin.admin_process_topup, name='admin_process_topup'),
    path('api/manual-trx/', views_admin.admin_manual_trx, name='admin_manual_trx'),
    path('api/update-limit/', views_admin.admin_update_limit,
         name='admin_update_limit'),
    path('api/agencies/', views_admin.admin_agency_api, name='admin_agency_api'),
    path('api/pending-topups/', views_admin.admin_topups_api,
         name='admin_topups_api'),

    path('api/invoices/', views_admin.admin_invoices_api,
         name='admin_invoices_api'),
    path('api/invoices/<int:invoice_id>/cancel/',
         views_admin.admin_invoice_cancel, name='admin_invoice_cancel'),
    path('api/invoices/<int:invoice_id>/refund/',
         views_admin.admin_invoice_refund, name='admin_invoice_refund'),

    path('api/invoices/<int:invoice_id>/details/',
         views_admin.admin_invoice_detail_api, name='admin_invoice_detail'),
    path('api/invoices/<int:invoice_id>/pay/',
         views_admin.admin_invoice_pay, name='admin_invoice_pay'),
    path('invoices/<int:invoice_id>/pdf/',
         views_admin.admin_invoice_pdf, name='admin_invoice_pdf'),

    path('api/agencies/simple/', views_admin.admin_agencies_simple_api,
         name='admin_agencies_simple'),
    path('api/invoices/bulk-pay/',
         views_admin.admin_bulk_pay, name='admin_bulk_pay'),


]
