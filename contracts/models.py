# CODE OK
from django.db import models

from clients.models import Client
from services.models import Service
from vendors.models import VendorService


class Currency(models.Model):
    """ A model to describe the abstract currency used for billing (may differ from payment) """

    ccy_type = models.CharField(max_length=10, db_column='type')
    ccy_virtual = models.CharField(max_length=3, null=True, blank=True)
    ccy_real = models.CharField(max_length=3, null=True, blank=True)

    def __str__(self):
        return self.ccy_type

    class Meta:
        db_table = 'pricing_types'
        verbose_name_plural = 'Currencies'
        ordering = ('ccy_type', )


class PaymentType(models.Model):
    """ A model to describe the type of charging for billing purposes associated with the contract """

    pmt_type = models.CharField(max_length=30, db_column='type')
    description = models.CharField(max_length=100, db_column='descr')

    def __str__(self):
        return self.description

    class Meta:
        db_table = 'payment_types'


class Contract(models.Model):
    """ A model to describe the Contract object """

    contract_id = models.AutoField(primary_key=True)
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, db_column='client_id', related_name='contracts')
    start_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.client.client_id} {self.client.reporting_name} - Contract {self.contract_id}/{self.start_date}'

    class Meta:
        db_table = 'contracts'


class Order(models.Model):
    """ A model to describe split of contracted services in abstract groups
    that may be charged and reported differently """

    order_id = models.AutoField(primary_key=True)
    contract = models.ForeignKey(
        Contract, on_delete=models.RESTRICT, db_column='contract_id', related_name='orders')
    start_date = models.DateField()
    end_date = models.DateField(null=True)
    description = models.TextField()
    ccy_type = models.ForeignKey(
        Currency, on_delete=models.RESTRICT, db_column='ccy_type', related_name='orders')
    tu_price = models.DecimalField(max_digits=5, decimal_places=3, default=0.000)
    payment_type = models.ForeignKey(
        PaymentType, on_delete=models.RESTRICT, db_column='payment_type', related_name='orders')
    is_active = models.BooleanField(default=True)
    # status = models.ForeignKey(
    #     OrderStatus, on_delete=models.RESTRICT, db_column='status_id', related_name='orders'
    # )

    @property
    def currency(self):
        return self.ccy_type.ccy_type

    @property
    def payment(self):
        return self.payment_type.description

    @property
    def vendors(self):
        vs = VendorService.objects\
            .filter(orderservice__order_id__exact=self.order_id)\
            .values_list('vendor_id', flat=True)
        return sorted(list(set(vs)))

    def __str__(self):
        vendors = ', '.join(str(el) for el in self.vendors)
        return f'{self.contract} - Vendors {vendors}'

    class Meta:
        db_table = 'orders'
        ordering = ['-is_active', '-start_date']


class OrderPrice(models.Model):
    """ A model to describe the prices associated with each service in an Order """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column='order_id')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, db_column='service_id')
    unit_price = models.DecimalField(max_digits=6, decimal_places=3, default=0.000)

    class Meta:
        db_table = 'order_prices'
        ordering = ['order', 'service__service_order']


class OrderService(models.Model):
    """ A model to link services to Orders """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column='order_id')
    service = models.ForeignKey(VendorService, on_delete=models.RESTRICT, db_column='vendor_service_id')

    class Meta:
        db_table = 'order_services'
