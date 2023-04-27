# CODE OK
from django.db import models
from shared.utils import period_validator


class PeriodField(models.CharField):
    """ Period field that accepts YYYY-MM format """

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 7
        kwargs['validators'] = [period_validator]
        super(PeriodField, self).__init__(*args, **kwargs)
