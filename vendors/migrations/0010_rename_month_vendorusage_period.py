# Generated by Django 4.1.7 on 2023-04-24 16:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0009_alter_vendorinputfile_month_alter_vendorusage_month'),
    ]

    operations = [
        migrations.RenameField(
            model_name='vendorusage',
            old_name='month',
            new_name='period',
        ),
    ]
