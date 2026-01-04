from django import forms
from .models import Port, Provider, ProviderRoute


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
