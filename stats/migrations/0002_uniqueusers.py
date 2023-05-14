# Generated by Django 4.1.7 on 2023-02-26 12:04

from django.db import migrations, models
import django.db.models.deletion
import month.models


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0003_vendor_iteco_name'),
        ('stats', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UniqueUsers',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', month.models.MonthField()),
                ('user_id', models.CharField(max_length=20)),
                ('vendor', models.ForeignKey(
                    db_column='vendor_id',
                    on_delete=django.db.models.deletion.RESTRICT,
                    related_name='unique_users',
                    to='vendors.vendor'
                )),
            ],
            options={
                'db_table': 'stats_uq_users',
                'unique_together': {('month', 'vendor', 'user_id')},
            },
        ),
    ]
