from django import forms
from shared.forms import PeriodForm
from .models import Report, Client


class ReportPeriodForm(PeriodForm):
    report = forms.ModelChoiceField(
        label="Choose report from the dropdown",
        queryset=Report.objects.all().order_by('file_name').filter(is_active=True),
        widget=forms.Select(
            attrs={'class': "form-control"})
    )


class ClientPeriodForm(PeriodForm):
    client = forms.ModelChoiceField(
        label='Choose client from dropdown',
        queryset=Client.objects.all().order_by('client_id').filter(is_billable=True, is_validated=True),
        widget=forms.Select(
            attrs={'class': "form-control"}
        )
    )
