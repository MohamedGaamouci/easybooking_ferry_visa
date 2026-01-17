from django.urls import path
from .. import views

app_name = 'finance'  # <--- Important for {% url 'finance:...' %}

urlpatterns = [
    # The Main Page
    path('dashboard/', views.finance_dashboard, name='dashboard'),

    # The AJAX Endpoint
    path('api/topup/submit/', views.submit_topup_ajax, name='submit_topup_ajax'),
    path('api/invoice/<int:invoice_id>/details/',
         views.invoice_detail_ajax, name='invoice_detail_ajax'),
    path('invoice/<int:invoice_id>/pdf/',
         views.download_invoice_pdf, name='download_invoice_pdf'),
    path('api/invoice/<int:invoice_id>/pay/',
         views.pay_invoice_ajax, name='pay_invoice_ajax'),
]
