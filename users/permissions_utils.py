ADMIN_ENDPOINTS = {
    'Dashboard': [
        'admin_cms',
        'admin_dashboard',
        'api_kpis',
        'api_performance_chart',
    ],
    'Finance': [
        'admin_accounting',
        'admin_ledger_api',
        'admin_process_topup',
        'admin_manual_trx',
        'admin_update_limit',
        'admin_agency_api',
        'admin_topups_api',
        'admin_invoices_api',
        'admin_invoice_cancel',
        'admin_invoice_refund',
        'admin_invoice_detail',
        'admin_invoice_pay',
        'admin_invoice_pdf',
        'admin_agencies_simple',
        'admin_bulk_pay',
        'get_credit_history'
    ],
    'Agencies': [
        'agency_management',
        'agency_create',
        'agency_update',
    ],
    'Users': [
        'user_management',
        'user_detail',
        'user_create',
        'user_update',
        'role_management',
        'role_create',
        'role_update',
        'role_detail'
    ],
    'Visas': [
        'admin_visa_app',
        'api_visa_details',
        'api_visa_update',
        'api_visa_destinations',
        'visa_create',
        'api_visa_schema',
        'visa_destination_create',
        'api_visa_destination_detail',
        'visa_destination_update',
        'api_admin_visa_list',
        'api_agency_search',
        'api_all_destinations'
    ],
    'Ferries': [
        'port_create',
        'port_detail',
        'port_update',
        'provider_create',
        'provider_update',
        'provider_detail',
        'ferries_requests',
        'admin_process',
        'api_admin_list',
        'api_admin_offer',
        'api_reject_offer',
        'api_attach_voucher',
        'admin_manage_schedule',
        'admin_save_pricing',
        'api_get_pricing',
        'api_delete_pricing',
        'api_admin_route_calendar',
        'api_delete_schedule_date',
        'api_pricing_structure'
    ],
    'Settings': [
        'admin_setting'
    ],
}

CLIENT_ENDPOINTS = {
    'Dashboard': [
        'client_dashboard',
        'api_agency_performance_chart',
        'api_agency_kpis',
        'api_user_info',
    ],
    'Finance': [
        'dashboard',  # finance dashboard
        'submit_topup_ajax',
        'invoice_detail_ajax',
        'download_invoice_pdf',
        'pay_invoice_ajax',
        'api_router'
    ],
    'Visas': [
        'visa_marketplace',
        'new_visa_application',
        'api_visa_schema',
        'api_visa_create',
        'api_visa_list',
        'api_visa_detail',
        'visa_applications',
        'api_visa_applications'
    ],
    'Ferries': [
        'ferries',
        'new_ferry',
        'api_ferry_list',
        'api_provider_routes',
        'api_create_demand',
        'api_update_demand',
        'api_demand_detail',
        'api_demand_respond',
        'api_available_dates',
        'api_calculate_price',
        'api_route_options',
        'api_get_pricing_client'
    ],
    'Settings': [
        'setting'
    ],
}
