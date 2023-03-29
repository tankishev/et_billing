from django import forms
from shared.utils import period_validator


class PeriodForm(forms.Form):
    period = forms.CharField(
        label='Enter period',
        max_length=7,
        validators=[period_validator],
        widget=forms.TextInput(
            attrs={'class': "form-control"}
        )
    )
