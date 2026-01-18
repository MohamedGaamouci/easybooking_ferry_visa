import logging
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def send_booking_notification(agency_name, manager_email, booking_ref, service_name, amount, invoice_pdf=None):
    subject = f"Easy Booking Confirmation: {booking_ref}"
    platform_email = "crm@easybooking.pro"

    context = {
        'agency_name': agency_name,
        'booking_ref': booking_ref,
        'service_name': service_name,  # Example: "Visa Application" or "Ferry Ticket"
        'amount': "{:,.2f}".format(amount),
    }

    html_content = render_to_string('emails/booking_confirmed.html', context)
    text_content = strip_tags(html_content)

    # Email to Manager
    msg = EmailMultiAlternatives(
        subject, text_content, settings.DEFAULT_FROM_EMAIL, [manager_email])
    msg.attach_alternative(html_content, "text/html")
    if invoice_pdf:
        msg.attach(f"Invoice_{booking_ref}.pdf",
                   invoice_pdf, "application/pdf")
    msg.send()

    # Simple text-only email for the platform admin
    send_mail(
        f"[NEW BOOKING] {service_name} - {agency_name}",
        f"New {service_name} recorded for {agency_name}. Ref: {booking_ref}. Total: {amount} DZD",
        settings.DEFAULT_FROM_EMAIL,
        [platform_email]
    )


logger = logging.getLogger(__name__)


def notify_balance_change(account, amount, change_type, reason):
    """
    Notifies about Wallet changes (Top-up, Payment, Refund).
    """
    print("hello from the norify balance chnager ...............")
    subject = f"Wallet Update: {change_type.capitalize()}"

    context = {
        'agency_name': account.agency.company_name,
        'amount': "{:,.2f}".format(amount),
        'new_balance': "{:,.2f}".format(account.balance),
        'reason': reason,
        'type': change_type,
    }

    html_content = render_to_string('emails/balance_update.html', context)
    text_content = strip_tags(html_content)

    recipients = [
        account.agency.manager.email,
        settings.DEFAULT_FROM_EMAIL,  # platform / CRM
    ]
    print("first email: ", account.agency.manager.email)
    print("second email: ", settings.DEFAULT_FROM_EMAIL)

    try:
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            recipients
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        print("hello from the end of norify balance chnager ...............")
    except Exception as e:
        logger.error(f"Balance change email failed: {e}")
