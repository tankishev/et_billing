# Generated by Django 4.1.7 on 2023-02-18 14:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Filter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filter_name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
            options={
                'db_table': 'service_filters',
            },
        ),
        migrations.CreateModel(
            name='FilterFunction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('func', models.CharField(max_length=15, unique=True)),
                ('description', models.CharField(max_length=50)),
            ],
            options={
                'db_table': 'service_filter_functions',
            },
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('service_id', models.AutoField(primary_key=True, serialize=False, verbose_name='Service ID')),
                ('service', models.CharField(max_length=20, verbose_name='Service group')),
                ('stype', models.CharField(blank=True, max_length=20, null=True, verbose_name='Service type')),
                ('desc_bg', models.CharField(max_length=255, verbose_name='Description BG')),
                ('desc_en', models.CharField(max_length=255, verbose_name='Description EN')),
                ('tu_cost', models.DecimalField(decimal_places=2, default=0, max_digits=6, verbose_name='TU cost')),
                ('usage_based', models.BooleanField(default=False, verbose_name='Transaction based')),
                ('skip_service_render', models.BooleanField(default=False, verbose_name='Hide in reports')),
                ('service_order', models.IntegerField(unique=True)),
                ('filter', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='filter_services',
                    to='services.filter'
                )),
            ],
            options={
                'db_table': 'services',
            },
        ),
        migrations.CreateModel(
            name='FilterConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(max_length=30)),
                ('value', models.CharField(blank=True, default='', max_length=15)),
                ('filter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services.filter')),
                ('func', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='filter_configs',
                    to='services.filterfunction'
                )),
            ],
            options={
                'db_table': 'service_filter_configs',
            },
        ),
    ]
