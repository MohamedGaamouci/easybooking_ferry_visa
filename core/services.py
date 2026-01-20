from ferries.models.ferry_request import FerryRequest  # Use your real model name
from visas.models.visa_application import VisaApplication  # Use your real model name
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from decimal import Decimal
from finance.models import Transaction, Account, TopUpRequest, InvoiceItem
from agencies.models import Agency
# Assuming you have these models, adjust names if needed:
# from bookings.models import VisaBooking, FerryBooking


class DashboardService:
    @staticmethod
    def get_kpis():
        today = timezone.now()
        first_of_month = today.replace(day=1, hour=0, minute=0, second=0)
        first_of_prev_month = (
            first_of_month - timedelta(days=1)).replace(day=1)

        # 1. Revenue & Growth
        curr_revenue = Transaction.objects.filter(
            transaction_type='payment',  # Adjust to your payment type key
            created_at__gte=first_of_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        prev_revenue = Transaction.objects.filter(
            transaction_type='payment',
            created_at__gte=first_of_prev_month,
            created_at__lt=first_of_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        growth = 0
        if prev_revenue > 0:
            growth = ((curr_revenue - prev_revenue) / prev_revenue) * 100

        # 2. Sales Split (Visa vs Ferry)
        # We look at InvoiceItems created this month
        items = InvoiceItem.objects.filter(
            invoice__created_at__gte=first_of_month)
        ferry_count = items.filter(description__icontains='Ferry').count()
        visa_count = items.filter(description__icontains='Visa').count()

        # 3. Agency Stats
        active_agencies = Agency.objects.filter(status='active').count()
        new_agencies = Agency.objects.filter(
            created_at__gte=today - timedelta(days=7)).count()

        return {
            'revenue': curr_revenue,
            'revenue_growth': round(growth, 1),
            'sales_total': ferry_count + visa_count,
            'ferry_count': ferry_count,
            'visa_count': visa_count,
            'active_agencies': active_agencies,
            'new_agencies_week': new_agencies,
            'pending_count': 0  # Will be updated by tasks
        }

    @staticmethod
    def get_urgent_tasks():
        tasks = []
        # 1. Pending Deposits
        topups = TopUpRequest.objects.filter(
            status='pending').select_related('account__agency')
        for t in topups:
            tasks.append({
                'type': 'deposit',
                'title': 'Approve Deposit',
                'meta': f"{t.account.agency.company_name} • {t.amount} DZD",
                'created_at': t.created_at,
                'icon': 'ph-fill ph-wallet',
                'color': 'amber'
            })

        # 2. Add Visa/Ferry logic here later when models are ready
        # visa_reqs = VisaBooking.objects.filter(status='submitted')...

        return sorted(tasks, key=lambda x: x['created_at'], reverse=True)

    @staticmethod
    def get_chart_data():
        days_data = []
        max_val = 1  # Prevent division by zero

        for i in range(6, -1, -1):
            date = timezone.now().date() - timedelta(days=i)
            # Sum payments for this specific day
            day_payments = Transaction.objects.filter(
                created_at__date=date, transaction_type='payment')

            # Simplified: splitting by description logic
            visa_rev = day_payments.filter(
                description__icontains='Visa').aggregate(s=Sum('amount'))['s'] or 0
            ferry_rev = day_payments.filter(
                description__icontains='Ferry').aggregate(s=Sum('amount'))['s'] or 0

            total = float(visa_rev + ferry_rev)
            if total > max_val:
                max_val = total

            days_data.append({
                'name': date.strftime('%a'),
                'visa_rev': float(visa_rev),
                'ferry_rev': float(ferry_rev),
            })

        # Calculate percentages for bar heights
        for day in days_data:
            day['visa_pct'] = (day['visa_rev'] / max_val) * 100
            day['ferry_pct'] = (day['ferry_rev'] / max_val) * 100

        return days_data

    @staticmethod
    def get_at_risk_agencies():
        return Account.objects.filter(balance__lt=10000).select_related('agency')[:5]
# core/services.py (Update)

    @staticmethod
    def get_recent_activity(limit=8):
        activity = []

        # 1. Recent Transactions (Top-ups, Payments)
        trans = Transaction.objects.all().select_related(
            'account__agency').order_by('-created_at')[:limit]
        for t in trans:
            activity.append({
                'message': f"{t.account.agency.company_name}: {t.description}",
                'timestamp': t.created_at,
                'color': 'emerald' if t.amount > 0 else 'blue'
            })

        # 2. Recent Agency Signups
        new_agencies = Agency.objects.order_by('-created_at')[:5]
        for a in new_agencies:
            activity.append({
                'message': f"New Agency Registered: {a.company_name}",
                'timestamp': a.created_at,
                'color': 'brand-500'
            })

        # Sort combined activity by time
        return sorted(activity, key=lambda x: x['timestamp'], reverse=True)[:limit]

# core/services.py (Update inside get_urgent_tasks)

    @staticmethod
    def get_urgent_tasks():
        tasks = []

        # 1. Pending Deposits (Your existing logic)
        topups = TopUpRequest.objects.filter(
            status='pending').select_related('account__agency')
        for t in topups:
            tasks.append({
                'type': 'deposit',
                'title': 'Approve Deposit',
                'meta': f"{t.account.agency.company_name} • {t.amount} DZD",
                'created_at': t.created_at,
                'icon': 'ph-fill ph-wallet',
                'color': 'amber'
            })

        # 2. Pending Visa Demands
        visas = VisaApplication.objects.filter(status='pending')[:5]
        for v in visas:
            tasks.append({
                'type': 'visa',
                'title': 'New Visa Demand',
                'meta': f"{v.agency.company_name} • {v.destination.country}",
                'created_at': v.created_at,
                'icon': 'ph-fill ph-passport',
                'color': 'purple'
            })

        # 3. Pending Ferry Demands
        ferries = FerryRequest.objects.filter(status='pending')[:5]
        for f in ferries:
            tasks.append({
                'type': 'ferry',
                'title': 'New Ferry Request',
                'meta': f"{f.agency.company_name} • {f.route}",
                'created_at': f.created_at,
                'icon': 'ph-fill ph-boat',
                'color': 'blue'
            })

        return sorted(tasks, key=lambda x: x['created_at'], reverse=True)
