# Generated by Django 4.1.7 on 2023-04-24 16:33

from django.db import migrations
import month.models


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0007_alter_uqustatsperiodclient_period_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='usagestats',
            name='month',
            field=month.models.MonthField(null=True),
        ),
    ]
