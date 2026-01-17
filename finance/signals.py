# finance/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from agencies.models import Agency
from .models import Account


@receiver(post_save, sender=Agency)
def create_agency_account(sender, instance, created, **kwargs):
    """
    Automatically create a Wallet (Account) when a new Agency is registered.
    """
    if created:
        Account.objects.create(agency=instance)

# Don't forget to register this signal in your apps.py!
