# Generated by Django 4.1.7 on 2023-02-18 14:29

from django.db import migrations, models
import django.db.models.deletion
import shared.models
import shared.utils
import vendors.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('services', '0001_initial'),
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('vendor_id', models.IntegerField(primary_key=True, serialize=False, verbose_name='Vendor ID')),
                ('description', models.CharField(max_length=100, verbose_name='Description EN')),
                ('is_reconciled', models.BooleanField(default=False)),
                ('client', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='vendors',
                    to='clients.client',
                    verbose_name='Client'
                )),
            ],
            options={
                'db_table': 'vendors',
            },
        ),
        migrations.CreateModel(
            name='VendorService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service', models.ForeignKey(
                    db_column='service_id',
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='vendor_services',
                    to='services.service'
                )),
                ('vendor', models.ForeignKey(
                    db_column='vendor_id',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='vendor_services',
                    to='vendors.vendor'
                )),
            ],
            options={
                'db_table': 'vendor_services',
            },
        ),
        migrations.CreateModel(
            name='VendorInputFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period', shared.models.PeriodField(max_length=7, validators=[shared.utils.period_validator])),
                ('file', models.FileField(max_length=255, upload_to=vendors.models.content_vendor_input_filename)),
                ('vendor', models.ForeignKey(
                    db_column='vendor_id',
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='input_files',
                    to='vendors.vendor'
                )),
            ],
            options={
                'db_table': 'vendor_input_files',
            },
        ),
        migrations.CreateModel(
            name='VendorFilterOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filter', models.ForeignKey(
                    db_column='filter_id',
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='filter_overrides',
                    to='services.filter'
                )),
                ('service', models.ForeignKey(
                    db_column='service_id',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='filter_overrides',
                    to='services.service'
                )),
                ('vendor', models.ForeignKey(
                    db_column='vendor_id',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='filter_overrides',
                    to='vendors.vendor'
                )),
            ],
            options={
                'db_table': 'vendor_filters_overrides',
            },
        ),
    ]
