# Generated by Django 4.1.7 on 2023-02-26 12:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0003_vendor_iteco_name'),
        ('stats', '0002_uniqueusers'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='UniqueUsers',
            new_name='UniqueUser',
        ),
    ]
