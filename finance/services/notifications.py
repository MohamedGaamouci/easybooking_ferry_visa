import logging
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def send_booking_notification(agency_name, manager_email, booking_ref, service_name, amount, invoice_pdf=None):
    subject = f"Easy Booking Confirmation: {booking_ref}"

    context = {
        'agency_name': agency_name,
        'booking_ref': booking_ref,
        'service_name': service_name,
        'amount': "{:,.2f}".format(amount),
    }

    html_content = render_to_string('emails/booking_confirmed.html', context)
    text_content = strip_tags(html_content)

    recipients = [
        manager_email,                   # Agency manager
        settings.DEFAULT_FROM_EMAIL,     # Platform / CRM
    ]

    for email in recipients:
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )

            msg.attach_alternative(html_content, "text/html")

            # Attach invoice ONLY for agency manager
            if invoice_pdf and email == manager_email:
                msg.attach(
                    f"Invoice_{booking_ref}.pdf",
                    invoice_pdf,
                    "application/pdf"
                )

            msg.send(fail_silently=True)

        except Exception as e:
            logger.error(
                f"Booking notification email failed for {email}: {e}"
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
    for email in recipients:
        try:
            msg = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [email],  # single recipient
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=True)
        except Exception as e:
            logger.error(f"Email failed for {email}: {e}")
