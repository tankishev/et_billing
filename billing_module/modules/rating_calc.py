from contracts.models import Client, Order
from stats.models import UsageTransaction
from vendors.models import Vendor
from collections import deque
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List
from django.db.models import Q
from django.db import transaction
from .processors import add_transaction_processor
from .transaction import RatedTransaction
from .utils import ChargeStatus, ChargeType
from ..models import PrepaidPackageCharge, OrderCharge

import logging
import re

logger = logging.getLogger(f'et_billing.{__name__}')


class BaseRater:
    """
    A class designed to handle the rating of transactions and calculation of charges for a given client.

    The BaseRater is responsible for loading client data, validating orders, loading transactions,
    and processing them through various charge objects. It handles the lifecycle of transaction rating,
    from data retrieval to the final calculation of charges. The class is designed to be extended
    or used with different types of charge objects and transaction models.

    Attributes:
        period_start (datetime): The start date and time of the rating period.
        period_end (datetime): The end date and time of the rating period.
        client (Client): The client for whom transactions are being rated.
        orders_data (list): A list of orders associated with the client.
        data_validated (bool): A flag indicating whether the orders data has been validated.
        unprocessed_transactions (deque): A queue of transactions that are yet to be processed.
        skipped_transactions (deque): A queue of transactions that have been skipped during processing.
        transaction_processors (List[BaseTransactionProcessor]): A list of charge objects used to process transactions.

    Methods:
        rate_client_transactions: Main method to initiate the rating process for a client.
    """

    def __init__(self, period: str) -> None:
        """
        Initializes the BaseRater with a given period.

        :param period: The period for which transactions are to be rated. Expected in format YYYY-MM.
        """

        self.period_start = None
        self.period_end = None
        self.period = period

        # DB data
        self.client = None
        self.orders_data = []
        self.data_validated = False

        # Transaction processing data
        self.unprocessed_transactions = deque()
        self.skipped_transactions = deque()
        self.transaction_processors = []

    @property
    def period(self):
        """
        :return: The current rating period.
        """
        return self._period

    @period.setter
    def period(self, value: str):
        """
        Sets the rating period including period_start and period_end.

        :param value: The new rating period to set.
        """

        pattern = r'^\d{4}-\d{2}$'
        if isinstance(value, str) and re.match(pattern, value):
            self.period_start = datetime.strptime(value, '%Y-%m')
            self.period_end = self.period_start + relativedelta(months=1)
            self._period = value
        else:
            logger.warning(f'Period {value} is not in format YYYY-MM')

    def rate_client_transactions(self, client_id: int) -> None:
        """
        Rates the transactions of a given client.

        :param client_id: The ID of the client whose transactions are to be rated.
        :raises Exception: Propagates any exceptions that occur during processing.
        """

        try:
            logger.info(f'Processing client {client_id}')
            self._load_client(client_id)

            if self.client is not None:
                self._load_orders_data()
                self._validate_orders_data()
                if self.data_validated:
                    self._load_charge_objects()
                    self._load_transactions()
                    self._rate_transactions()
                    self._print_rated_transactions_summary()
                    self._save_charges()

        except Exception as e:
            logger.error(f'Error: {e}')
            raise

    def _load_client(self, client_id: int) -> None:
        """
        Loads the client data based on the provided client ID.

        :param client_id: The ID of the client to load.
        :raises TypeError: If the client_id is not of type int.
        :raises Client.DoesNotExist: If no client is found with the given ID.
        :raises Exception: For any other exceptions that occur.
        """

        logger.info(f'Loading client data')

        try:
            if not isinstance(client_id, int):
                raise TypeError(f"Expected X to be an int, got {type(client_id).__name__}")

            # Get Client
            client = Client.objects.get(pk=client_id)
            self.client = client

            # Check if all accounts are fully mapped and load transactions
            unreconciled_vendors = Vendor.objects.filter(client=client, is_reconciled=False)
            if unreconciled_vendors.exists():
                logger.warning(f'Some accounts for client {client} are not fully mapped')
                return

        except Client.DoesNotExist:
            logger.warning(f'Client with id {client_id} does not exist')

        except Exception as e:
            logger.error(f'Error: {e}')
            raise

    def _load_orders_data(self) -> None:
        """
        Loads Order's data relevant to the current client and rating period.
        Filters Order based on various criteria including payment type and date range.
        """

        logger.info(f'Loading orders data')
        self.orders_data.clear()

        orders = Order.objects.filter(
            Q(contract__client=self.client)
        ).filter(
            Q(start_date__lte=self.period_end.date()) &
            (Q(end_date__gte=self.period_start.date()) | Q(end_date__isnull=True)) |
            Q(orderpackages__prepaid_package__is_active=True)
        ).prefetch_related(
            'orderpackages_set__prepaid_package',
            'orderprice_set',
            'orderservice_set__service'
        ).order_by('start_date', 'order_id').distinct()
        self.orders_data = list(orders)

    def _validate_orders_data(self) -> None:
        """
        Validates the loaded orders data to ensure there are no duplicate services in more than one active order.
        Sets the 'data_validated' attribute based on the validation result.
        """

        logger.info('Validating order data')

        vs_ids = [os.service.id for order in self.orders_data for os in order.orderservice_set.all() if order.is_active]

        if len(vs_ids) != len(set(vs_ids)):
            duplicates = set(x for x in vs_ids if vs_ids.count(x) > 1)
            logger.warning(f'...FAILED: AccountServices {duplicates} present in more than one active Order')
            self.data_validated = False
        else:
            self.data_validated = True

    def _load_charge_objects(self) -> None:
        """
        Initializes different types of charge objects based on the payment type of each order.
        """

        self.transaction_processors.clear()
        if not self.orders_data:
            logger.warning('No orders data')
        else:
            logger.info('Setting up charge objects')
            for order in self.orders_data:
                add_transaction_processor(order, processors_list=self.transaction_processors)

    def _load_transactions(self) -> None:
        """
        Loads transactions for the current client and rating period.
        Filters transactions based on vendor client and timestamp.
        Processes and sorts transactions before adding them to the unprocessed transactions queue.
        :raises Exception: For any exceptions that occur during the loading process.
        """

        logger.info(f'Loading transactions')

        try:
            self.unprocessed_transactions.clear()
            usage_transactions = UsageTransaction.objects.filter(
                vendor__client=self.client,
                timestamp__gte=self.period_start,
                timestamp__lt=self.period_end
            ).order_by('timestamp', 'thread_id')
            if usage_transactions.exists():
                vs_list = list(set(os.service for order in self.orders_data for os in order.orderservice_set.all()))
                transactions_list = list(usage_transactions)
                transactions_list = sorted(transactions_list, key=lambda x: x.timestamp)
                for el in transactions_list:
                    rated_transaction = RatedTransaction(el)
                    rated_transaction.set_vs(vs_list)
                    self.unprocessed_transactions.append(rated_transaction)
            else:
                logger.warning(f'No UsageTransactions to load')

        except Exception as e:
            logger.error(f'Error: {e}')

    def _rate_transactions(self) -> None:
        """
        Processes each transaction from the unprocessed transactions queue.
        Determines the charge object in the transaction is to be processed.
        Appends any skipped transactions to the skipped_transactions queue.
        """

        logger.info(f'Loading transactions')

        self.skipped_transactions.clear()
        while self.unprocessed_transactions:
            unprocessed_transaction = self.unprocessed_transactions.popleft()
            transaction_processed = False

            for processor in self.transaction_processors:
                if processor.process_transaction(unprocessed_transaction):
                    transaction_processed = True
                    break

            if not transaction_processed:
                self.skipped_transactions.append(unprocessed_transaction)

    def _print_rated_transactions_summary(self):
        for processor in self.transaction_processors:
            print(processor.charges_summary)

    def _save_charges(self) -> None:
        """
        Saves the calculated charges for orders and prepaid packages to the database.

        This method gathers charge details from each transaction processor and creates records for OrderCharge
        and PrepaidPackageCharge. OrderCharge records are created for each service charge, including details like
        charge date, order, vendor, and charged units. Existing OrderCharge records for the same period and order are
        deleted. PrepaidPackageCharge records are prepared for charges related to prepaid or shared packages.
        """

        order_charges = []
        prepaid_package_charges = []
        charge_date = self.period_end.date()
        invoice_charges = {}

        for processor in self.transaction_processors:
            order = processor.order
            charge_type = processor.charge_type

            # Prepare record for order charges
            for vendor_id, service_charges in processor.service_charges.items():
                for service_id, charge_data in service_charges.items():
                    unit_count = charge_data.get('count', 0)
                    charge_amount = charge_data.get('charge', 0)
                    order_charges.append(
                        OrderCharge(
                            period=charge_date,
                            order=order,
                            payment_type_id=charge_type.value,
                            vendor_id=vendor_id,
                            service_id=service_id,
                            service_count=unit_count,
                            charged_units=charge_amount
                        )
                    )

                    if charge_type == ChargeType.INVOICE:
                        invoice_ccy = invoice_charges.setdefault(order.ccy_type, {})


            # Prepare record for charges to prepaid packages
            if charge_type in (ChargeType.PREPAID, ChargeType.PREPAID_SHARED):
                prepaid_package_charges.append(
                    PrepaidPackageCharge(
                        charge_date=charge_date,
                        charge_status_id=ChargeStatus.PENDING.value,
                        charged_units=processor.total_charges,
                        prepaid_package=processor.prepaid_package
                    )
                )

        with transaction.atomic():
            OrderCharge.objects\
                .filter(order__contract__client=self.client, period=charge_date)\
                .delete()
            PrepaidPackageCharge.objects\
                .filter(charge_status_id=ChargeStatus.PENDING.value, charge_date=charge_date)\
                .delete()

            if order_charges:
                OrderCharge.objects.bulk_create(order_charges)
            if prepaid_package_charges:
                PrepaidPackageCharge.objects.bulk_create(prepaid_package_charges)
