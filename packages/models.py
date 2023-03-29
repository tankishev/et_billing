from django.db import models
from month.models import MonthField
from contracts.models import Order


class PrepaidPackage(models.Model):
    order = models.ForeignKey(Order, on_delete=models.RESTRICT, db_column='order_id', related_name='packages')
    purchased_units = models.IntegerField(default=0)
    purchased_amount = models.DecimalField(max_digits=12, decimal_places=5, default=0.00000)
    transferred_units = models.IntegerField(default=0)
    transferred_amount = models.DecimalField(max_digits=12, decimal_places=5, default=0.00000)

    @property
    def starting_units(self):
        return self.purchased_units + self.transferred_units

    @property
    def starting_amount(self):
        return self.purchased_amount + self.transferred_amount

    @property
    def avg_price(self):
        return self.starting_amount / self.starting_units

    @property
    def remaining_units(self):
        usage_data = self.usage.values_list('used_units', flat=True)
        used_units = sum(usage_data)
        return self.starting_units - used_units

    @property
    def balance(self):
        return self.remaining_units * self.avg_price

    class Meta:
        db_table = 'order_packages'


class PackageUsage(models.Model):
    period = MonthField()
    package = models.ForeignKey(PrepaidPackage, on_delete=models.RESTRICT, db_column='package_id', related_name='usage')
    used_units = models.IntegerField(default=0)

    class Meta:
        db_table = 'order_package_usage'
