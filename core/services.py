from ferries.models.ferry_request import FerryRequest  # Use your real model name
from visas.models.visa_application import VisaApplication  # Use your real model name
from django.utils import timezone
from finance.models import Account, TopUpRequest
from django.db.models import Sum, Q
from datetime import timedelta
from decimal import Decimal
from finance.models import Invoice
from django.contrib.contenttypes.models import ContentType


class KPI:
    @staticmethod
    def get_last_month_revenue(start_date=None, end_date=None):
        """
        Calculates revenue from invoices. 
        If start_date and end_date are provided, it filters by that range.
        Otherwise, it defaults to the previous calendar month.
        """

        # Default Logic: Previous Calendar Month
        if not start_date or not end_date:
            today = timezone.now().date()
            first_day_curr_month = today.replace(day=1)
            # Last day of prev month is 1 day before the 1st of current month
            end_date = first_day_curr_month - timedelta(days=1)
            start_date = end_date.replace(day=1)

        # Query Invoices within the range
        invoices_in_range = Invoice.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        # 1. Total Potential Revenue (Sum of all invoices)
        total_invoiced = invoices_in_range.aggregate(
            total=Sum('total_amount'))['total'] or Decimal('0.00')

        # 2. Collected Revenue (Paid Invoices)
        paid_revenue = invoices_in_range.filter(
            status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        # 3. Outstanding Revenue (Unpaid or Partially Paid)
        unpaid_revenue = invoices_in_range.filter(
            status='unpaid'
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

        return {
            'total': total_invoiced,
            'paid': paid_revenue,
            'unpaid': unpaid_revenue,
            'start_date': start_date,
            'end_date': end_date,
            'label': start_date.strftime('%b %d') + " - " + end_date.strftime('%b %d, %Y')
        }

    @staticmethod
    def get_sales_volume(start_date=None, end_date=None):
        """
        Returns the count of successful sales.
        Visa: Must be 'completed'
        Ferry: Must be 'confirmed'
        """
        # Date Logic: Defaults to previous calendar month
        if not start_date or not end_date:
            today = timezone.now().date()
            first_day_curr_month = today.replace(day=1)
            end_date = first_day_curr_month - timedelta(days=1)
            start_date = end_date.replace(day=1)

        # Count Successful Visa Applications
        visa_count = VisaApplication.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status='completed'  # Only count finished processes
        ).count()

        # Count Successful Ferry Requests
        ferry_count = FerryRequest.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status='confirmed'  # Only count finalized bookings
        ).count()

        return {
            'ferry': ferry_count,
            'visa': visa_count,
            'total': ferry_count + visa_count,
            'start_date': start_date,
            'end_date': end_date
        }

    @staticmethod
    def get_pending_counts():
        """
        Returns the current count of items awaiting admin action.
        Visa: status = 'pending'
        Ferry: status = 'pending'
        """
        # Count Visas currently in 'pending' state
        visa_pending = VisaApplication.objects.filter(status='new').count()

        # Count Ferry requests currently in 'pending' state
        # Adjust 'pending' to your actual status key (e.g., 'submitted' or 'pending_confirmation')
        ferry_pending = FerryRequest.objects.filter(status='pending').count()

        return {
            'visa_pending': visa_pending,
            'ferry_pending': ferry_pending,
            'total_pending': visa_pending + ferry_pending
        }

    @staticmethod
    def get_active_agencies_count(start_date=None, end_date=None):
        """
        Returns the count of unique agencies that submitted 
        at least one Visa or Ferry request within the period.
        """
        # Date Logic: Defaults to previous calendar month
        if not start_date or not end_date:
            today = timezone.now().date()
            first_day_curr_month = today.replace(day=1)
            end_date = first_day_curr_month - timedelta(days=1)
            start_date = end_date.replace(day=1)

        # Get unique agency IDs from VisaApplications
        visa_agency_ids = VisaApplication.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values_list('agency_id', flat=True)

        # Get unique agency IDs from FerryRequests
        ferry_agency_ids = FerryRequest.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values_list('agency_id', flat=True)

        # Combine sets to get unique IDs across both services
        # Sets automatically handle duplicates (an agency active in both counts as 1)
        active_ids = set(visa_agency_ids) | set(ferry_agency_ids)

        return {
            'active_count': len(active_ids),
            'active_agencies_ids': active_ids,
            'start_date': start_date,
            'end_date': end_date
        }


class DashboardService:
    @staticmethod
    def get_urgent_tasks():
        """
        Fetches pending Top-Up requests and formats them as tasks.
        Uses the correct relation path: TopUpRequest -> Account -> Agency
        """
        tasks = []

        # We use double underscores (__) to reach the Agency from the Account
        pending_topups = TopUpRequest.objects.filter(
            status='pending'
        ).select_related('account__agency').order_by('-created_at')

        for topup in pending_topups:
            # Safely get the company name through the account relation
            agency_name = topup.account.agency.company_name if topup.account and topup.account.agency else "Unknown Agency"

            tasks.append({
                'type': 'topup',
                'title': f"Deposit: {agency_name}",
                'meta': f"Amount: {topup.amount:,.0f} DZD",
                'created_at': topup.created_at.isoformat() if topup.created_at else None,
                'icon': 'ph-bold ph-bank',
                'color': 'amber',
            })

        return tasks

    @staticmethod
    def get_at_risk_agencies(threshold=35000):
        """
        Identifies agencies with balances below the threshold.
        """
        at_risk = []

        # Query accounts with low balances
        # We assume Account has a 'balance' field and a 'agency' relation
        low_balance_accounts = Account.objects.filter(
            credit_limit__lt=threshold
        ).select_related('agency').order_by('credit_limit')

        for acc in low_balance_accounts:
            at_risk.append({
                'agency_name': acc.agency.company_name,
                'credit_limit': float(acc.credit_limit),
                'balance': float(acc.balance),
                'unpaid_hold': float(acc.unpaid_hold),
                'id': acc.agency.id,
                # Determine "urgency" color based on how low it is
                'status_color': 'rose' if acc.balance < 2000 else 'amber'
            })

        return at_risk

    from datetime import timedelta, date

    def _get_date_list(self, start_date, end_date):
        """Helper to create a list of dates between start and end."""
        if not start_date or not end_date:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=6)

        delta = end_date - start_date
        return [start_date + timedelta(days=i) for i in range(delta.days + 1)]

    def get_weekly_revenue_breakdown(self, start_date=None, end_date=None, agency=None):
        """Method 1: Revenue using Invoice model, filtered by Item ContentType."""
        date_list = self._get_date_list(start_date, end_date)
        data = []

        # Get ContentTypes once to avoid repeated queries
        visa_type = ContentType.objects.get_for_model(VisaApplication)
        ferry_type = ContentType.objects.get_for_model(FerryRequest)

        for day in date_list:
            # Base filters for the Invoice
            base_filters = Q(created_at__date=day) & Q(
                status__in=['paid', 'unpaid'])
            if agency:
                base_filters &= Q(agency=agency)

            # 1. Sum total_amount for Invoices that have at least one 'Ferry' item
            ferry_rev = Invoice.objects.filter(
                base_filters,
                items__content_type=ferry_type
            ).distinct().aggregate(total=Sum('total_amount'))['total'] or 0

            # 2. Sum total_amount for Invoices that have at least one 'Visa' item
            visa_rev = Invoice.objects.filter(
                base_filters,
                items__content_type=visa_type
            ).distinct().aggregate(total=Sum('total_amount'))['total'] or 0

            data.append({
                'day': day.strftime('%a'),
                'ferry': float(ferry_rev),
                'visa': float(visa_rev)
            })
        return data

    def get_weekly_volume_breakdown(self, start_date=None, end_date=None, agency=None):
        """Method 2: Booking Counts (Directly from Service Models)."""
        date_list = self._get_date_list(start_date, end_date)
        data = []

        for day in date_list:
            f_filters = Q(created_at__date=day, status='confirmed')
            v_filters = Q(created_at__date=day, status='completed')

            if agency:
                f_filters &= Q(agency=agency)
                v_filters &= Q(agency=agency)

            data.append({
                'day': day.strftime('%a'),
                'ferry': FerryRequest.objects.filter(f_filters).count(),
                'visa': VisaApplication.objects.filter(v_filters).count()
            })
        return data
