from django import forms
from django.core.validators import FileExtensionValidator

from shared.forms import PeriodForm
from vendors.models import Vendor


class FileUploadForm(PeriodForm):
    """ A PeriodForm with a field for file upload """

    file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=('zip', ))],
        widget=forms.FileInput(
            attrs={'class': "form-control"}
        )
    )


class VendorFileUploadForm(PeriodForm):
    """ A PeriodForm with a field for file upload and VendorID selector"""

    vendor = forms.ModelChoiceField(
        label='Choose account from dropdown',
        queryset=Vendor.objects.all().order_by('client_id').filter(
            client__is_billable=True,
            client__is_validated=True,
            is_active=True
        ),
        widget=forms.Select(
            attrs={'class': "form-control"}
        )
    )
    file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=('csv', ))],
        widget=forms.FileInput(
            attrs={'class': "form-control"}
        )
    )
