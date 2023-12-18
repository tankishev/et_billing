from django.db import models

from clients.models import Client
from vendors.models import Vendor
from services.models import Service
from contracts.models import Currency


class RatedTransaction(models.Model):
    timestamp = models.DateTimeField()
    billing_client = models.ForeignKey(
        Client, on_delete=models.RESTRICT, db_column='billing_client_id', related_name='rated_transactions')
    vendor = models.ForeignKey(
        Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name='rated_transactions')
    service = models.ForeignKey(
        Service, on_delete=models.RESTRICT, db_column='service_id', related_name='rated_transactions')
    ccy_type = models.ForeignKey(
        Currency, on_delete=models.RESTRICT, db_column='ccy_type')
    cost = models.DecimalField(max_digits=6, decimal_places=3)
    charge_user = models.BooleanField(default=False)
