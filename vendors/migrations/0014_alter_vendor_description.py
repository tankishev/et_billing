# Generated by Django 4.1.7 on 2024-02-01 10:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0013_alter_vendorservice_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vendor',
            name='description',
            field=models.CharField(max_length=100, verbose_name='Description EN'),
        ),
    ]
