from django.db import models
from month.models import MonthField
from clients.models import Client
from services.models import Service
from vendors.models import Vendor


class UsageStats(models.Model):
    """ Model to store vendor service UsageStats """

    period = MonthField()
    vendor = models.ForeignKey(
        Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name='usage_stats')
    service = models.ForeignKey(
        Service, on_delete=models.RESTRICT, db_column='service_id', related_name='usage_stats')
    unit_count = models.IntegerField()

    class Meta:
        db_table = 'stats_usage'


class UniqueUser(models.Model):
    """ Models to store unique user PIDs for each period and vendor """

    month = MonthField()
    vendor = models.ForeignKey(
        Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name='unique_users')
    user_id = models.CharField(max_length=30)
    country = models.CharField(max_length=5, null=True, blank=True)

    class Meta:
        db_table = 'stats_uq_users'
        unique_together = ('month', 'vendor', 'user_id')


class UquStatsPeriod(models.Model):
    """ Model to store aggregated stats regarding unique users per month """

    period = MonthField(unique=True)
    cumulative = models.IntegerField()
    uqu_month = models.IntegerField()
    uqu_new = models.IntegerField()

    class Meta:
        db_table = 'stats_uqu_period'


class UquStatsPeriodClient(models.Model):
    """ Model to store aggregated stats regarding unique users per client per month """

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
    """ Model to store aggregated stats regarding unique users per vendor per month """

    period = MonthField()
    vendor = models.ForeignKey(
        Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name='uqu_stats')
    cumulative = models.IntegerField()
    uqu_month = models.IntegerField()
    uqu_new = models.IntegerField()

    class Meta:
        db_table = 'stats_uqu_period_vendor'
        unique_together = ('period', 'vendor')


class UquStatsPeriodCountries(models.Model):
    """ Model to store aggregated stats regarding unique users per country and period """

    period = MonthField()
    country = models.CharField(max_length=5)
    cumulative = models.IntegerField()
    uqu_month = models.IntegerField()
    uqu_new = models.IntegerField()

    class Meta:
        db_table = 'stats_uqu_period_country'
        unique_together = ('period', 'country')


class TransactionStatus(models.Model):
    status_type = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=50)

    class Meta:
        db_table = 'stats_transaction_statuses'


class UsageTransaction(models.Model):
    timestamp = models.DateTimeField()
    vendor = models.ForeignKey(
        Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name='usage_transactions')
    thread_id = models.CharField(max_length=12)
    transaction_id = models.BigIntegerField()
    transaction_status = models.ForeignKey(
        TransactionStatus, on_delete=models.RESTRICT, db_column='status_id')
    service = models.ForeignKey(
        Service, on_delete=models.RESTRICT, db_column='service_id', related_name='usage_transactions', null=True)
    charge_user = models.BooleanField(default=False)
    bio_pin = models.BooleanField(default=False)

    class Meta:
        db_table = 'stats_usage_transactions'

    @property
    def period(self):
        return self.timestamp.strftime("%Y-%m")

    @property
    def date(self):
        return self.timestamp.strftime("%Y-%m-%d")
