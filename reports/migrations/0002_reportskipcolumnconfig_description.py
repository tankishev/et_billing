# Generated by Django 4.1.7 on 2023-02-21 10:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportskipcolumnconfig',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
