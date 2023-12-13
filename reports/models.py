from django.db import models
from month.models import MonthField
import os

from clients.models import Client
from vendors.models import Vendor


class ReportType(models.Model):
    """ !!! TO BE DEPRECIATED An object to record the type of report """

    type = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.type

    class Meta:
        db_table = "report_type"


class ReportLanguage(models.Model):
    """ An object to record the language of the report """

    language = models.CharField(max_length=3, unique=True)

    def __str__(self):
        return self.language

    class Meta:
        db_table = "report_languages"


class ReportSkipColumnConfig(models.Model):
    """ An object to record configurations of which columns have to be skipped when rendering a report """

    skip_columns = models.CharField(max_length=30, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.skip_columns

    class Meta:
        db_table = "report_skip_columns"


class Report(models.Model):
    """ An object to record a billing report configuration """

    file_name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    include_details = models.BooleanField(default=True)
    show_pids = models.BooleanField(default=False)
    report_type = models.ForeignKey(
        ReportType, on_delete=models.RESTRICT, db_column='report_type', related_name='reports')
    language = models.ForeignKey(
        ReportLanguage, on_delete=models.RESTRICT, related_name='reports')
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='reports')
    vendors = models.ManyToManyField(
        Vendor, db_table='report_vendors', related_name='reports')
    skip_columns = models.ForeignKey(
        ReportSkipColumnConfig, on_delete=models.RESTRICT, db_column='skip_columns', related_name='reports')

    def __str__(self):
        return self.file_name

    class Meta:
        db_table = 'reports'


class ReportFileType(models.Model):
    """ An object to record the type of reports we are storing """

    description = models.CharField(max_length=100)
    default_folder = models.CharField(max_length=20)
    default_name = models.CharField(unique=True, max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'report_file_types'


def content_report_file_filename(instance, filename):
    """ Generates filename for a ReportFile. Uses default folder and default name depending on report file type """

    if instance.type.default_name:
        filename = instance.type.default_name
    return os.path.join('output/%s/%s/%s' % (instance.type.default_folder, instance.period, filename))


class ReportFile(models.Model):
    """ An object to record the generated billing report files """

    period = MonthField()
    file = models.FileField(max_length=255, upload_to=content_report_file_filename)
    report = models.ForeignKey(
        Report, on_delete=models.RESTRICT, db_column='report_id', related_name='report_files')
    type = models.ForeignKey(
        ReportFileType, on_delete=models.RESTRICT, related_name='report_files')

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    @property
    def list_name(self):
        return self.filename

    def __str__(self):
        return f'{self.period} - {self.report.file_name}'

    class Meta:
        db_table = 'report_files'


class TransactionStatus(models.Model):
    """ !!! NOT USED """
    status_type = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=50)

    class Meta:
        db_table = 'transaction_statuses'
