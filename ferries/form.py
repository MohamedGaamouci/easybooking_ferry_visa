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


class FerryRequestForm(forms.ModelForm):
    # We add route_id explicitly because the model expects a 'route' object,
    # but the API receives a 'route_id' integer.
    route_id = forms.IntegerField(required=True)

    class Meta:
        model = FerryRequest
        fields = ['trip_type', 'departure_date',
                  'return_date', 'accommodation']

    def clean(self):
        cleaned_data = super().clean()
        trip_type = cleaned_data.get('trip_type')
        dep_date = cleaned_data.get('departure_date')
        ret_date = cleaned_data.get('return_date')

        # 1. Date Logic
        if trip_type == 'round':
            if not ret_date:
                self.add_error(
                    'return_date', "Return date is required for round trips.")
            elif dep_date and ret_date and ret_date < dep_date:
                self.add_error(
                    'return_date', "Return date cannot be before departure.")

        # 2. Prevent Past Dates (Optional, good practice)
        if dep_date and dep_date < datetime.date.today():
            self.add_error('departure_date',
                           "Departure cannot be in the past.")

        return cleaned_data

    def clean_route_id(self):
        rid = self.cleaned_data['route_id']
        # Ensure route exists and is active
        if not ProviderRoute.objects.filter(pk=rid, is_active=True).exists():
            raise ValidationError("The selected route is invalid or inactive.")
        return rid


class FerryRequestForm(forms.ModelForm):
    route_id = forms.IntegerField(required=True)

    class Meta:
        model = FerryRequest
        fields = ['trip_type', 'departure_date',
                  'return_date', 'accommodation']

    def clean(self):
        cleaned_data = super().clean()
        route_id = cleaned_data.get('route_id')
        dep_date = cleaned_data.get('departure_date')

        # New Schedule Validation
        if route_id and dep_date:
            # Check if this date is actually in the RouteSchedule table
            is_available = RouteSchedule.objects.filter(
                route_id=route_id,
                date=dep_date,
                is_active=True
            ).exists()

            if not is_available:
                self.add_error(
                    'departure_date', "The selected provider does not have a departure on this date.")

        return cleaned_data
