from django.db import models
from month.models import MonthField
import os

from clients.models import Client


class Vendor(models.Model):
    """ A Vendor is an object in Iteco to link a client to an API key """

    vendor_id = models.IntegerField(primary_key=True, verbose_name='Vendor ID')
    description = models.CharField(max_length=100, verbose_name='Description EN', unique=True)
    is_reconciled = models.BooleanField(default=False)
    client = models.ForeignKey(
        Client, on_delete=models.RESTRICT, verbose_name='Client', related_name='vendors')
    iteco_name = models.CharField(max_length=100, verbose_name='Iteco name')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.vendor_id}_{self.description}'

    class Meta:
        db_table = 'vendors'


class VendorService(models.Model):
    """ VendorService objects hold the link which services are enabled for each Vendor """

    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, db_column='vendor_id', related_name='vendor_services')
    service = models.ForeignKey(
        'services.Service', on_delete=models.RESTRICT, db_column='service_id', related_name='vendor_services')

    def __str__(self):
        return f'{self.vendor.vendor_id} - {self.service}'

    class Meta:
        db_table = 'vendor_services'
        ordering = ('service__service_order',)


# DEPRECIATED - REMOVE
class VendorFilterOverride(models.Model):
    """ VendorFilterOverride object tracks the ServiceFilters overrides for respective Vendors """

    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, db_column='vendor_id')
    service = models.ForeignKey(
        'services.Service', on_delete=models.CASCADE, db_column='service_id')
    filter = models.ForeignKey(
        'services.Filter', on_delete=models.RESTRICT, db_column='filter_id')

    class Meta:
        db_table = 'vendor_filters_overrides'


def content_vendor_input_filename(instance, filename):
    return os.path.join('input/%s/%s' % (instance.period, filename))


class VendorInputFile(models.Model):
    """ An object to record the Iteco vendor files """
    period = MonthField()
    file = models.FileField(max_length=255, upload_to=content_vendor_input_filename)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name='input_files'
    )
    is_active = models.BooleanField(default=True)

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def list_name(self):
        return str(self.vendor)

    def __str__(self):
        return f'{self.period} - {self.vendor}'

    class Meta:
        db_table = 'vendor_input_files'


# NOT IMPLEMENTED
class VendorUsage(models.Model):
    period = MonthField()
    vendor = models.ForeignKey(
        Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name='vendor_usage')
    service = models.ForeignKey(
        'services.Service', on_delete=models.RESTRICT, db_column='service_id', related_name='vendor_usage')
    unit_count = models.IntegerField()

    class Meta:
        db_table = 'vendor_usage'
