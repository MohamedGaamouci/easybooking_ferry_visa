from django.db import transaction
from datetime import date
from django.core.exceptions import ValidationError
from ferries.models.provider_route import ProviderRoute, RouteSchedule, RoutePriceComponent
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
    def calculate_total_price(route_id, trip_type, departure_date, return_date, passengers, vehicle_data):
        total_net = 0
        total_selling = 0
        breakdown = []

        # 1. Load Route Data
        try:
            outbound_route = ProviderRoute.objects.get(pk=route_id)
            return_route = None
            if trip_type == 'round':
                # Find the reverse route based on origin/destination swap
                return_route = ProviderRoute.objects.filter(
                    origin=outbound_route.destination,
                    destination=outbound_route.origin,
                    provider=outbound_route.provider,
                    is_active=True
                ).first()
        except ProviderRoute.DoesNotExist:
            raise ValidationError("Invalid Route ID")

        # 2. Process Passengers
        for idx, p in enumerate(passengers, 1):
            p_type = p.get('type')

            # --- Ongoing Leg (A -> B) ---
            # Passenger Price
            out_pax_rule = RoutePriceComponent.objects.filter(
                route=outbound_route, category='pax', item_name=p_type).first()
            if out_pax_rule:
                total_net += out_pax_rule.net_price
                total_selling += out_pax_rule.selling_price
                breakdown.append({'item': f"Pax {idx} ({p_type}) - Out",
                                 'price': float(out_pax_rule.selling_price)})

            # Accommodation Price (Only if selected)
            out_acc = p.get('outbound_accommodation')
            if out_acc:  # This handles None, empty string, or "none" from frontend
                out_acc_rule = RoutePriceComponent.objects.filter(
                    route=outbound_route, category='accommodation', item_name=out_acc).first()
                if out_acc_rule:
                    total_net += out_acc_rule.net_price
                    total_selling += out_acc_rule.selling_price
                    breakdown.append(
                        {'item': f"Acc {idx} ({out_acc}) - Out", 'price': float(out_acc_rule.selling_price)})

            # --- Return Leg (B -> A) ---
            if trip_type == 'round' and return_route:
                # Passenger Price
                ret_pax_rule = RoutePriceComponent.objects.filter(
                    route=return_route, category='pax', item_name=p_type).first()
                if ret_pax_rule:
                    total_net += ret_pax_rule.net_price
                    total_selling += ret_pax_rule.selling_price
                    breakdown.append(
                        {'item': f"Pax {idx} ({p_type}) - Ret", 'price': float(ret_pax_rule.selling_price)})

                # Accommodation Price (Only if selected)
                ret_acc = p.get('return_accommodation')
                if ret_acc:
                    ret_acc_rule = RoutePriceComponent.objects.filter(
                        route=return_route, category='accommodation', item_name=ret_acc).first()
                    if ret_acc_rule:
                        total_net += ret_acc_rule.net_price
                        total_selling += ret_acc_rule.selling_price
                        breakdown.append(
                            {'item': f"Acc {idx} ({ret_acc}) - Ret", 'price': float(ret_acc_rule.selling_price)})

        # 3. Vehicle (Ongoing only as requested)
        if vehicle_data and vehicle_data.get('type'):
            v_type = vehicle_data.get('type')
            v_rule = RoutePriceComponent.objects.filter(
                route=outbound_route, category='vehicle', item_name=v_type).first()
            if v_rule:
                total_net += v_rule.net_price
                total_selling += v_rule.selling_price
                breakdown.append(
                    {'item': f"Vehicle ({v_type})", 'price': float(v_rule.selling_price)})

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
        price_id = data.get('id')

        # 1. Check for overlaps (excluding the current record if editing)
        FerryPriceAdminService.check_for_overlaps(
            route_id, data['category'], data['item_name'],
            data['start_date'], data['end_date'],
            exclude_id=price_id
        )

        # 2. Use the ID to find the record for an update,
        # or use all fields to create a new one if no ID exists.
        if price_id:
            # UPDATE case: Find by ID and update all fields
            price_item, created = RoutePriceComponent.objects.update_or_create(
                id=price_id,
                defaults={
                    'route_id': route_id,
                    'category': data['category'],
                    'item_name': data['item_name'],
                    'start_date': data['start_date'],
                    'end_date': data['end_date'],
                    'net_price': data.get('net_price', 0),
                    'selling_price': data['selling_price']
                }
            )
        else:
            # CREATE case: Standard creation
            price_item = RoutePriceComponent.objects.create(
                route_id=route_id,
                category=data['category'],
                item_name=data['item_name'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                net_price=data.get('net_price', 0),
                selling_price=data['selling_price']
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
