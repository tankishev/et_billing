# Generated by Django 4.1.7 on 2023-05-21 10:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0011_rename_month_vendorinputfile_period'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vendor',
            name='description',
            field=models.CharField(max_length=100, unique=True, verbose_name='Description EN'),
        ),
    ]
