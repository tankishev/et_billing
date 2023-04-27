# CODE OK
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.urls import resolve


def period_validator(value):
    """ Validator for YYYY-MM periods """

    period_err_message = _(
        "“%(value)s” is not a valid period. "
        "Accepted periods are in format yyyy-mm and between 2021-01 and 2029-12"
    )
    rv = RegexValidator(
        r'^202[0-9]{1}-[0-1]{1}[0-9]{1}$',
        message=period_err_message
    )
    rv(value)
    year, month = [int(x) for x in value.split('-')]
    if 0 < month < 13 and 2020 < year < 2030:
        return
    raise ValidationError(period_err_message, params={"value": value})


def get_parent_object_from_request(obj, request):
    """
    Returns the parent object from the request or None.

    Note that this only works for Inlines, because the `parent_model`
    is not available in the regular admin.ModelAdmin as an attribute.
    """

    resolved = resolve(request.path_info)
    if resolved.kwargs:
        return obj.parent_model.objects.get(pk=resolved.kwargs["object_id"])
    return None


class DictToObjectMixin:
    """ Simple class that can be used to convert simple dictionary into objects with properties """

    def add_attributes(self, **config_data):
        """ Adds attributes to the object """

        for k, v in config_data.items():
            if hasattr(self, k):
                continue
            setattr(self, k, v)
