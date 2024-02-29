# Generated by Django 4.1.7 on 2024-02-28 05:43

from django.db import migrations, models
import django.db.models.deletion
import month.models


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0014_alter_vendor_description'),
        ('contracts', '0007_order_end_date'),
        ('services', '0002_alter_service_options'),
        ('billing_module', '0002_alter_orderpackages_order_ordercharge'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='prepaidpackage',
            name='is_active',
        ),
        migrations.AddField(
            model_name='prepaidpackage',
            name='status',
            field=models.IntegerField(choices=[(0, 'PRE_ACTIVE'), (1, 'ACTIVE'), (2, 'PRE_CLOSED'), (3, 'CLOSED')], default=0),
        ),
        migrations.AlterField(
            model_name='ordercharge',
            name='order',
            field=models.ForeignKey(db_column='order_id', on_delete=django.db.models.deletion.CASCADE, related_name='order_charges', to='contracts.order'),
        ),
        migrations.AlterField(
            model_name='ordercharge',
            name='service',
            field=models.ForeignKey(db_column='service_id', on_delete=django.db.models.deletion.RESTRICT, related_name='order_charges', to='services.service'),
        ),
        migrations.AlterField(
            model_name='ordercharge',
            name='vendor',
            field=models.ForeignKey(db_column='vendor_id', on_delete=django.db.models.deletion.RESTRICT, related_name='order_charges', to='vendors.vendor'),
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period', month.models.MonthField()),
                ('charged_units', models.DecimalField(decimal_places=2, max_digits=10)),
                ('ccy_type', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='contracts.currency')),
                ('charge_status', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to='billing_module.chargestatus')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invoices', to='contracts.order')),
            ],
            options={
                'db_table': 'billing_order_invoices',
            },
        ),
    ]
