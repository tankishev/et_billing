from django import forms
from django.core.validators import FileExtensionValidator

from shared.forms import PeriodForm


class FileUploadForm(PeriodForm):
    """ A PeriodForm with a field for file upload """

    file = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=('zip', ))],
        widget=forms.FileInput(
            attrs={'class': "form-control"}
        )
    )
