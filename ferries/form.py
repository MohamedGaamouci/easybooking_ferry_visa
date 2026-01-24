import datetime
from django.core.exceptions import ValidationError
from django import forms

from ferries.models.provider_route import RouteSchedule
from .models import Port, Provider, ProviderRoute
from .models import FerryRequest, ProviderRoute


class PortForm(forms.ModelForm):
    class Meta:
        model = Port
        fields = ['name', 'code', 'city', 'country', 'is_active']

    def clean_code(self):
        # Force uppercase code (e.g., 'alg' -> 'ALG')
        code = self.cleaned_data.get('code')
        if code:
            return code.upper()
        return code

# --- PROVIDER FORM (This was missing) ---


class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        # These fields must match the inputs in your HTML modal
        fields = ['name', 'code', 'contact_email',
                  'contact_phone', 'logo', 'is_active']

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            return code.upper()
        return code


class ProviderRoutesForm(forms.ModelForm):
    class meta:
        model = ProviderRoute()
        fields = '__all__'


# --- Helper: JSON Validator ---

def validate_passenger_structure(passengers):
    """
    Validates the list of passengers from the JSON payload.
    """
    if not isinstance(passengers, list) or len(passengers) == 0:
        return "Passenger list cannot be empty."

    required_keys = ['first_name', 'last_name', 'birth_date', 'type']

    for idx, p in enumerate(passengers):
        # Check keys
        if not all(k in p for k in required_keys):
            return f"Passenger #{idx+1} is missing required fields (Name, DOB, Type)."

        # Check empty strings
        if not str(p['first_name']).strip() or not str(p['last_name']).strip():
            return f"Passenger #{idx+1} has an empty name."

    return None

# --- Main Form ---


class FerryRequestForm(forms.Form):
    route_id = forms.IntegerField(required=True)
    trip_type = forms.ChoiceField(
        choices=[('oneway', 'One Way'), ('round', 'Round Trip')], required=True)
    departure_date = forms.DateField(required=True)
    return_date = forms.DateField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        rid = cleaned_data.get('route_id')
        trip_type = cleaned_data.get('trip_type')
        dep_date = cleaned_data.get('departure_date')
        ret_date = cleaned_data.get('return_date')

        # 1. Ensure Route Exists
        if rid and not ProviderRoute.objects.filter(pk=rid, is_active=True).exists():
            raise ValidationError("The selected route is invalid.")

        # 2. Schedule Check (Ongoing)
        if rid and dep_date:
            if not RouteSchedule.objects.filter(route_id=rid, date=dep_date, is_active=True).exists():
                self.add_error('departure_date',
                               "No departure available on this date.")

        # 3. Round Trip Logic
        if trip_type == 'round':
            if not ret_date:
                self.add_error('return_date', "Return date is required.")
            elif dep_date and ret_date < dep_date:
                self.add_error(
                    'return_date', "Return date cannot be before departure.")

            # Schedule Check (Return Leg)
            outbound = ProviderRoute.objects.get(pk=rid)
            reverse_route = ProviderRoute.objects.filter(
                origin=outbound.destination, destination=outbound.origin).first()
            if reverse_route and ret_date:
                if not RouteSchedule.objects.filter(route=reverse_route, date=ret_date, is_active=True).exists():
                    self.add_error(
                        'return_date', "No return ferry available on this date.")

        return cleaned_data
