from django.db import transaction
from datetime import date
from django.core.exceptions import ValidationError
from ferries.models.provider_route import RouteSchedule, RoutePriceComponent
from django.db.models import Q


class FerryPricingService:
    @staticmethod
    def get_available_dates(route_id):
        """Returns a list of active dates for a specific route."""
        return list(RouteSchedule.objects.filter(
            route_id=route_id,
            is_active=True,
            date__gte=date.today()
        ).values_list('date', flat=True))

    @staticmethod
    def is_date_available(route_id, travel_date):
        """Quick check for the frontend/form validation."""
        return RouteSchedule.objects.filter(
            route_id=route_id,
            date=travel_date,
            is_active=True
        ).exists()

    @staticmethod
    def calculate_total_price(route_id, travel_date, passengers, vehicle=None, accommodation=None):
        """
        Calculates the sum of all individual components for a specific date.
        Uses Atomic to ensure consistency during the complex lookup.
        """
        if not FerryPricingService.is_date_available(route_id, travel_date):
            raise ValidationError(
                f"No active trip scheduled for {travel_date}")

        total_net = 0
        total_selling = 0
        breakdown = []

        # 1. Calculate Passengers
        for p in passengers:
            p_type = p.get('type')
            price_row = RoutePriceComponent.objects.filter(
                route_id=route_id,
                category='pax',
                item_name=p_type,
                start_date__lte=travel_date,
                end_date__gte=travel_date
            ).first()

            if price_row:
                total_net += price_row.net_price
                total_selling += price_row.selling_price
                breakdown.append(
                    {'item': f"Passenger ({p_type})", 'price': float(price_row.selling_price)})
            else:
                raise ValidationError(
                    f"No pricing found for passenger type: {p_type}")

        # 2. Calculate Vehicle
        if vehicle and vehicle.get('type'):
            v_type = vehicle.get('type')
            price_row = RoutePriceComponent.objects.filter(
                route_id=route_id,
                category='vehicle',
                item_name=v_type,
                start_date__lte=travel_date,
                end_date__gte=travel_date
            ).first()

            if price_row:
                total_net += price_row.net_price
                total_selling += price_row.selling_price
                breakdown.append(
                    {'item': f"Vehicle ({v_type})", 'price': float(price_row.selling_price)})

        # 3. Calculate Accommodation
        if accommodation:
            price_row = RoutePriceComponent.objects.filter(
                route_id=route_id,
                category='accommodation',
                item_name=accommodation,
                start_date__lte=travel_date,
                end_date__gte=travel_date
            ).first()

            if price_row:
                total_net += price_row.net_price
                total_selling += price_row.selling_price
                breakdown.append({'item': f"Accommodation ({accommodation})", 'price': float(
                    price_row.selling_price)})

        return {
            'total_net': total_net,
            'total_selling': total_selling,
            'breakdown': breakdown
        }


class FerryScheduleService:
    @staticmethod
    def get_route_calendar(route_id):
        return RouteSchedule.objects.filter(route_id=route_id).order_by('date')

    @transaction.atomic
    @staticmethod
    def add_available_date(route_id, date_obj):
        """Adds a single available date atomically."""
        return RouteSchedule.objects.get_or_create(route_id=route_id, date=date_obj)

    @transaction.atomic
    @staticmethod
    def bulk_add_dates(route_id, date_list):
        """Atomic bulk creation to ensure all or nothing."""
        schedules = [RouteSchedule(route_id=route_id, date=d)
                     for d in date_list]
        return RouteSchedule.objects.bulk_create(schedules, ignore_conflicts=True)

    @transaction.atomic
    @staticmethod
    def delete_date(schedule_id):
        return RouteSchedule.objects.filter(id=schedule_id).delete()


class FerryPriceAdminService:
    @staticmethod
    def check_for_overlaps(route_id, category, item_name, start_date, end_date, exclude_id=None):
        overlaps = RoutePriceComponent.objects.filter(
            route_id=route_id,
            category=category,
            item_name=item_name
        ).filter(
            Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
        )

        if exclude_id:
            overlaps = overlaps.exclude(id=exclude_id)

        if overlaps.exists():
            raise ValidationError(
                "This date range overlaps with an existing price for this item.")

    @transaction.atomic
    @staticmethod
    def create_or_update_price(route_id, data):
        """Atomic update/create with overlap validation."""
        FerryPriceAdminService.check_for_overlaps(
            route_id, data['category'], data['item_name'],
            data['start_date'], data['end_date'],
            exclude_id=data.get('id')
        )

        price_item, created = RoutePriceComponent.objects.update_or_create(
            route_id=route_id,
            category=data['category'],
            item_name=data['item_name'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            defaults={
                'net_price': data.get('net_price', 0),
                'selling_price': data['selling_price']
            }
        )
        return price_item

    @staticmethod
    def get_route_pricing_grid(route_id):
        # Note: order_back changed to order_by for standard Django syntax
        return RoutePriceComponent.objects.filter(route_id=route_id).order_by('start_date')

    @transaction.atomic
    @staticmethod
    def delete_price_component(component_id):
        return RoutePriceComponent.objects.filter(id=component_id).delete()
