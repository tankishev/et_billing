from django.db import models
from decimal import Decimal
from month.models import MonthField
from clients.models import Client
from contracts.models import Currency, Order, PaymentType
from services.models import Service
from vendors.models import Vendor

BGN_TO_EUR = Decimal('1') / Decimal('1.95583')


class PrepaidPackage(models.Model):
    """
    Represents a prepaid package in the billing system.

    This model stores the details of prepaid packages including start, expiry,
    and closing dates, description, balance details, and associated currency.

    Attributes:
        start_date (DateField): The starting date of the package.
        expiry_date (DateField): The expiry date of the package.
        closing_date (DateField): Optional date when the package was closed.
        description (TextField): Optional description of the package.
        original_balance (DecimalField): The initial balance of the package.
        currency (ForeignKey): The currency associated with the package, linked to the Currency model.
        original_rate (DecimalField): The original conversion rate for the package.
        average_rate (DecimalField): The average conversion rate calculated for the package.
        is_active (BooleanField): Flag indicating if the package is currently active.
    """

    start_date = models.DateField()
    expiry_date = models.DateField()
    closing_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    original_balance = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.RESTRICT, db_column='ccy_id')
    original_rate = models.DecimalField(max_digits=7, decimal_places=5, default=1)
    average_rate = models.DecimalField(max_digits=7, decimal_places=5, default=1)
    is_active = models.BooleanField(default=True)

    @property
    def available_balance(self):
        """
        Calculates the available balance of the prepaid package.

        This balance is computed by aggregating all charges (credits and debits)
        associated with the package and applying them to the original balance.
        """

        aggregated_charges = self.charges.aggregate(
            total_credits=models.Sum('charged_units', filter=models.Q(is_credit=True)),
            total_debits=models.Sum('charged_units', filter=models.Q(is_credit=False))
        )

        total_credits = aggregated_charges['total_credits'] or 0
        total_debits = aggregated_charges['total_debits'] or 0
        return self.original_balance + total_credits - total_debits

    @property
    def balance(self):
        """
        Calculates the current balance of the prepaid package.

        Similar to `available_balance`, but only considers posted transactions.
        """

        aggregated_charges = self.charges.filter(charge_status_id=2).aggregate(
            total_credits=models.Sum('charged_units', filter=models.Q(is_credit=True)),
            total_debits=models.Sum('charged_units', filter=models.Q(is_credit=False))
        )

        total_credits = aggregated_charges['total_credits'] or 0
        total_debits = aggregated_charges['total_debits'] or 0
        return self.original_balance + total_credits - total_debits

    @property
    def value(self):
        """
        Calculates the current value of the prepaid package.

        The value is determined by multiplying the average rate with the current balance.
        """

        return self.average_rate * self.balance

    @property
    def value_eur(self):
        """
        Calculates the value of the prepaid package in EUR.

        Converts the package value to EUR based on a predefined conversion rate.
        """
        currency_rate = BGN_TO_EUR if self.currency in (1, 3) else 1
        return self.value * currency_rate

    def save(self, *args, **kwargs):
        if not self.pk:  # Checking if the object is new
            self.average_rate = self.original_rate
        super(PrepaidPackage, self).save(*args, **kwargs)

    class Meta:
        db_table = 'billing_prepaid_packages'


class ChargeStatus(models.Model):
    """
    Represents the status of a charge in the billing system.

    This simple model holds various statuses that a charge can have, described through
    a short text.

    Attributes:
        description (CharField): Description of the charge status.
    """

    description = models.CharField(max_length=10)

    class Meta:
        db_table = 'billing_charge_statuses'


class PrepaidPackageCharge(models.Model):
    """
    Details a single charge against a prepaid package.

    This model records each individual charge or credit against a prepaid package,
    including the date, the associated prepaid package, the amount, whether it's
    a credit or debit, and the status of the charge.

    Attributes:
        charge_date (DateField): The date of the charge.
        prepaid_package (ForeignKey): The prepaid package that the charge applies to.
        charged_units (DecimalField): The amount of the charge.
        is_credit (BooleanField): Indicates if the charge is a credit (increasing balance).
        charge_status (ForeignKey): The status of the charge, linked to the ChargeStatus model.
    """

    charge_date = models.DateField()
    prepaid_package = models.ForeignKey(PrepaidPackage, on_delete=models.CASCADE, related_name='charges')
    charged_units = models.DecimalField(max_digits=10, decimal_places=2)
    is_credit = models.BooleanField(default=False)
    charge_status = models.ForeignKey(ChargeStatus, on_delete=models.RESTRICT)

    class Meta:
        db_table = 'billing_package_charges'


class OrderPackages(models.Model):
    """
    Represents the relationship between orders and prepaid packages.

    This model is used to link orders to prepaid packages, effectively associating
    a prepaid package with a specific order.

    Attributes:
        order (ForeignKey): The order associated with the prepaid package.
        prepaid_package (ForeignKey): The prepaid package associated with the order.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column='order_id')
    prepaid_package = models.ForeignKey(PrepaidPackage, on_delete=models.CASCADE)

    class Meta:
        db_table = 'billing_order_packages'
        ordering = ['prepaid_package__start_date']


class OrderCharge(models.Model):

    period = MonthField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column='order_id', related_name="order_charges")
    payment_type = models.ForeignKey(PaymentType, on_delete=models.RESTRICT)
    vendor = models.ForeignKey(Vendor, on_delete=models.RESTRICT, db_column='vendor_id', related_name="order_charges")
    service = models.ForeignKey(
        Service, on_delete=models.RESTRICT, db_column='service_id', related_name="order_charges")
    service_count = models.IntegerField()
    charged_units = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'billing_order_charges'


class Invoice(models.Model):
    period = MonthField()
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='invoices')
    ccy_type = models.ForeignKey(Currency, on_delete=models.RESTRICT)
    charge_status = models.ForeignKey(ChargeStatus, on_delete=models.RESTRICT)

    class Meta:
        db_table = 'billing_invoices'


class InvoiceCharge(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='invoice_charges')
    description = models.CharField(max_length=100)
    service_count = models.IntegerField()
    charged_units = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'billing_invoice_charges'
