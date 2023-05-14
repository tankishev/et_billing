# Generated by Django 4.1.7 on 2023-02-18 13:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ClientCountry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=3)),
                ('country', models.CharField(max_length=30)),
            ],
            options={
                'db_table': 'client_countries',
            },
        ),
        migrations.CreateModel(
            name='Industry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('industry', models.CharField(max_length=30, unique=True, verbose_name='Industry')),
            ],
            options={
                'verbose_name_plural': 'Industries',
                'db_table': 'client_industries',
            },
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('client_id', models.IntegerField(primary_key=True, serialize=False, verbose_name='Client ID')),
                ('legal_name', models.CharField(max_length=100, verbose_name='Legal name')),
                ('reporting_name', models.CharField(max_length=100, verbose_name='Reporting name')),
                ('client_group', models.CharField(blank=True, max_length=100, null=True, verbose_name='Client group')),
                ('is_billable', models.BooleanField(default=False, verbose_name='Is billable')),
                ('is_validated', models.BooleanField(default=False, verbose_name='Is validated')),
                ('country', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='clients',
                    to='clients.clientcountry'
                )),
                ('industry', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='clients',
                    to='clients.industry',
                    verbose_name='Client industry'
                )),
            ],
            options={
                'db_table': 'client_data',
            },
        ),
    ]
