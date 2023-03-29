from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator

from shared.forms import PeriodForm
from .models import Vendor


def validate_vendor(value):
    if value not in [el.get('vendor_id') for el in Vendor.objects.values('vendor_id')]:
        raise ValidationError(
            _('%(value)s is not a valid vendor_id'),
            params={'value': value},
        )


class VendorPeriodForm(PeriodForm):
    pk = forms.IntegerField(
        label='Enter vendor_id',
        widget=forms.NumberInput(
            attrs={'class': "form-control"}
        ),
        validators=[validate_vendor]
    )


class FileUploadForm(PeriodForm):
    file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=('zip', ))],
        widget=forms.FileInput(
            attrs={'class': "form-control"}
        )
    )
