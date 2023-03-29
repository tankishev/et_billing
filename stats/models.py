from django.db import models
from services.models import Service
from shared.models import PeriodField
from clients.models import Client
from vendors.models import Vendor
from month.models import MonthField


class UsageStats(models.Model):
    period = PeriodField()
    vendor = models.ForeignKey(
        Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name='usage_stats')
    service = models.ForeignKey(
        Service, on_delete=models.RESTRICT, db_column='service_id', related_name='usage_stats')
    unit_count = models.IntegerField()

    class Meta:
        db_table = 'stats_usage'


class UniqueUser(models.Model):
    month = MonthField()
    vendor = models.ForeignKey(
        Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name='unique_users')
    user_id = models.CharField(max_length=20)

    class Meta:
        db_table = 'stats_uq_users'
        unique_together = ('month', 'vendor', 'user_id')


class UquStatsPeriod(models.Model):
    period = MonthField(unique=True)
    cumulative = models.IntegerField()
    uqu_month = models.IntegerField()
    uqu_new = models.IntegerField()

    class Meta:
        db_table = 'stats_uqu_period'


class UquStatsPeriodClient(models.Model):
    period = MonthField()
    client = models.ForeignKey(
        Client, on_delete=models.RESTRICT, db_column='client_id', related_name='uqu_stats')
    cumulative = models.IntegerField()
    uqu_month = models.IntegerField()
    uqu_new = models.IntegerField()

    class Meta:
        db_table = 'stats_uqu_period_client'
        unique_together = ('period', 'client')


class UquStatsPeriodVendor(models.Model):
    period = MonthField()
    vendor = models.ForeignKey(
        Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name='uqu_stats')
    cumulative = models.IntegerField()
    uqu_month = models.IntegerField()
    uqu_new = models.IntegerField()

    class Meta:
        db_table = 'stats_uqu_period_vendor'
        unique_together = ('period', 'vendor')