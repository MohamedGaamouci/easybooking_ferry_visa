from django import forms
from .models import CustomUser


class UserForm(forms.ModelForm):
    # Password is handled manually in the view (to hash it)
    # required=False allows us to leave it empty during updates
    password = forms.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'state',
            'role',
            'agency',
            'is_active'
        ]
