# Generated by Django 4.1.7 on 2023-03-17 17:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='packageusage',
            name='used_units',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='prepaidpackage',
            name='purchased_units',
            field=models.IntegerField(default=0),
        ),
    ]