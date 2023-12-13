from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from shared.forms import PeriodForm
from .models import Client
from .models import Vendor


def validate_vendor(value):
    """ Check if value is a valid vendor_id """

    if value not in [el.get('vendor_id') for el in Vendor.objects.values('vendor_id')]:
        raise ValidationError(
            _('%(value)s is not a valid account ID'),
            params={'value': value},
        )


class VendorPeriodForm(PeriodForm):
    """ A PeriodForm with a field for vendor_id """

    pk = forms.IntegerField(
        label='Enter account ID',
        widget=forms.NumberInput(
            attrs={'class': "form-control"}
        ),
        validators=[validate_vendor]
    )


class UniqueUsersForm(forms.Form):
    """ Form to select inputs for extracting Unique Users information """

    SCOPE_CHOICES = (
        ('1', 'Client'),
        ('2', 'All'),
    )

    scope_select = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=SCOPE_CHOICES,
        label='Select scope',
        initial='1',
    )

    client = forms.ModelChoiceField(
        queryset=Client.objects.all().order_by('client_id').filter(is_billable=True, is_validated=True),
        widget=forms.Select(
            attrs={'class': "form-control"}
        ),
        required=False,
    )

    PERIOD_CHOICES = (
        ('1', 'Period'),
        ('2', 'Range'),
        ('3', 'All'),
    )

    period_select = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=PERIOD_CHOICES,
        initial='1',
    )

    period_start = forms.CharField(
        max_length=7,
        widget=forms.TextInput(
            attrs={'class': "form-control", 'placeholder': "From period"}
        ),
        required=False,
    )

    period_end = forms.CharField(
        max_length=7,
        widget=forms.TextInput(
            attrs={'class': "form-control", 'placeholder': "To period"},
        ),
        required=False,
    )

    def clean_period_start(self):
        period_select = self.data.get('period_select')
        period_start = self.data.get('period_start')
        if period_select != '3':
            return period_is_valid(period_start)

    def clean_period_end(self):
        period_select = self.data.get('period_select')
        period_end = self.data.get('period_end')
        if period_select == '2':
            return period_is_valid(period_end)

    def clean_client(self):
        scope_select = self.data.get('scope_select')
        client_id = self.data.get('client')
        if scope_select == '1' and not client_id.isnumeric():
            raise ValidationError('Please select a client')
        return self.cleaned_data.get('client')


def period_is_valid(period):
    """ Period validator to be used in the UniqueUsersForm class """
    period_err_message = _(
        "“%(value)s” is not a valid period. "
        "Accepted periods are in format yyyy-mm and between 2018-09 and latest usage upload"
    )
    rv = RegexValidator(
        r'^20[1-2][0-9]{1}-[0-1]{1}[0-9]{1}$',
        message=period_err_message
    )
    rv(period)
    year, month = [int(x) for x in period.split('-')]
    if year == 2018 and 8 < month < 13:
        return period
    elif 0 < month < 13:
        return period
    raise ValidationError(period_err_message, params={"value": period})
