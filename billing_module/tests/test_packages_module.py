from django.test import TestCase
from datetime import date
from ..modules.packages import transfer_balance
from ..modules.utils import ChargeStatus
from ..models import PrepaidPackage, PrepaidPackageCharge
from contracts.models import Currency


class TransferBalanceTests(TestCase):

    def setUp(self):
        # Create common data for all tests
        self.currency_type = Currency.objects.get(pk=1)
        self.today = str(date.today())

        # Create two prepaid packages with same currency and active status
        self.package1 = PrepaidPackage.objects.create(
            start_date=self.today,
            expiry_date='2030-12-31',
            original_balance=10,
            currency=self.currency_type,
            original_rate=1.5,
            average_rate=1.5,
        )
        self.package2 = PrepaidPackage.objects.create(
            start_date=self.today,
            expiry_date='2030-12-31',
            original_balance=10,
            currency=self.currency_type,
        )

    def test_successful_balance_transfer(self):
        # Setting up initial balances
        self.package1.original_balance = 100
        self.package2.original_rate = 50
        self.package1.save()
        self.package2.save()

        # Perform the balance transfer
        result = transfer_balance(self.package1, self.package2)

        # Assertions
        self.assertTrue(result)
        self.assertEqual(self.package1.balance, 0)
        self.assertEqual(self.package2.balance, 150)
        self.assertFalse(self.package1.is_active)
        self.assertEqual(PrepaidPackageCharge.objects.count(), 2)

    def test_transfer_with_inactive_package(self):
        self.package1.is_active = False
        self.package1.save()

        result = transfer_balance(self.package1, self.package2)

        self.assertFalse(result)
        self.assertNotEqual(self.package1.balance, 0)

    def test_transfer_with_mismatched_currency(self):
        different_currency = Currency.objects.exclude(pk=self.package2.currency).first()
        self.package2.currency = different_currency
        self.package2.save()

        package2_starting_balance = self.package2.balance
        result = transfer_balance(self.package1, self.package2)

        self.assertFalse(result)
        self.assertEqual(self.package2.balance, package2_starting_balance)

    def test_transfer_with_insufficient_balance(self):
        self.package1.original_balance = 0
        self.package1.save()

        result = transfer_balance(self.package1, self.package2)

        self.assertFalse(result)

    def test_transfer_with_custom_transfer_date(self):
        custom_date = '2023-01-12'
        result = transfer_balance(self.package1, self.package2, transfer_date=custom_date)

        self.assertTrue(result)
        self.assertTrue(PrepaidPackageCharge.objects.filter(charge_date=custom_date).exists())

    def test_transfer_with_pending_transaction(self):
        result = transfer_balance(self.package1, self.package2, post_transaction=False)

        self.assertTrue(result)
        self.assertTrue(PrepaidPackageCharge.objects.filter(charge_status=ChargeStatus.PENDING.value).exists())
