# Generated by Django 4.1.7 on 2023-04-24 15:40

from django.db import migrations
import month.models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0007_transactionstatus'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportfile',
            name='month',
            field=month.models.MonthField(null=True),
        ),
    ]
