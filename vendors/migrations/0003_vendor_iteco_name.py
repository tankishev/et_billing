# Generated by Django 4.1.7 on 2023-02-22 05:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0002_vendorinputfile_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='iteco_name',
            field=models.CharField(default='TEMP', max_length=100, verbose_name='Iteco name'),
            preserve_default=False,
        ),
    ]
