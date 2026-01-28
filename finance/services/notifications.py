import logging
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)


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
            if invoice_pdf:
                msg.attach(
                    f"Invoice_{booking_ref}.pdf",
                    invoice_pdf,
                    "application/pdf"
                )

            msg.send(fail_silently=True)
            logger.info(f"notificaiton was sent to: {email}")
        except Exception as e:
            logger.error(
                f"Booking notification email failed for {email}: {e}"
            )


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
            logger.info(f"notificaiton was sent to: {email}")
        except Exception as e:
            logger.error(f"Email failed for {email}: {e}")


def notify_status_change(booking_obj, old_status):
    """
    General notification for status changes (Visa or Ferry).
    """
    # 1. Determine the service name dynamically
    if hasattr(booking_obj, 'route'):
        service_label = f"Ferry: {booking_obj.route.__str__()}"
    elif hasattr(booking_obj, 'destination'):
        service_label = f"Visa: {booking_obj.destination.visa_type}"

    subject = f"Booking Status Update: {booking_obj.reference}"

    # 2. Prepare Context using human-readable labels
    context = {
        'agency_name': booking_obj.agency.company_name,
        'booking_ref': booking_obj.reference,
        'service_name': service_label,
        # We use Django's get_status_display to get "Ready for Collection" instead of "ready"
        'old_status': old_status.replace('_', ' ').capitalize(),
        'new_status': booking_obj.get_status_display(),
        'updated_at': booking_obj.updated_at,
    }

    html_content = render_to_string('emails/status_update.html', context)
    text_content = strip_tags(html_content)

    recipients = [
        booking_obj.agency.manager.email,
        settings.DEFAULT_FROM_EMAIL,
        # "gaamoucimohamed@gmail.com",
        # 'crm.easybooking@gmail.com'
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

            # Attachment logic: if status is 'ready' for Visa or 'confirmed' for Ferry,
            # and there is a file, you could attach it here.
            if hasattr(booking_obj, 'visa_doc') and booking_obj.visa_doc and booking_obj.status == 'ready':
                msg.attach_file(booking_obj.visa_doc.path)
            elif hasattr(booking_obj, 'voucher') and booking_obj.voucher and booking_obj.status == 'confirmed':
                msg.attach_file(booking_obj.voucher.path)

            msg.send(fail_silently=True)
            logger.info(f"notificaiton was sent to: {email}")

        except Exception as e:
            logger.error(f"Status update email failed for {email}: {e}")


def notify_new_request_received(request_obj, Type=None):
    """
    General notification for any new service request (Visa, Ferry, etc.)
    """
    # Determine the service name dynamically
    if Type == 'Ferry':  # It's a Ferry
        service_label = "Ferry"
    elif Type == 'Visa':  # Assuming Visa model has this
        service_label = "Visa"
    else:
        service_label = request_obj.__class__.__name__

    subject = f"New Reservation Received: {request_obj.reference}"

    context = {
        'agency_name': request_obj.agency.company_name,
        'booking_ref': request_obj.reference,
        'service_name': service_label,
        'amount': "{:,.2f}".format(request_obj.selling_price),
    }

    html_content = render_to_string('emails/new_booking.html', context)
    text_content = strip_tags(html_content)

    recipients = [
        request_obj.agency.manager.email,
        settings.DEFAULT_FROM_EMAIL,
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
            msg.send(fail_silently=True)
            logger.info(f"notificaiton was sent to: {email}")
        except Exception as e:
            logger.error(f"General notification failed for {email}: {e}")
