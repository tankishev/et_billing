from contracts.models import Client, Order
from stats.models import UsageTransaction
from vendors.models import Vendor
from collections import deque
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List
from django.db.models import Q
from django.db import transaction
from .processors import get_transaction_processors
from .transaction import RatedTransaction
from .utils import get_last_date_of_period
from ..models import OrderCharge, PackageStatus

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
        self.charge_date = None
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
            self.charge_date = get_last_date_of_period(value)
            self._period = value
        else:
            logger.warning(f'Period {value} is not in format YYYY-MM')

    def rate_client_transactions(self, client_id: int, verbose=False) -> None:
        """
        Rates the transactions of a given client.

        :param client_id: The ID of the client whose transactions are to be rated.
        :param verbose: If TRUE the method will print processor summary to console.
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
                    self._save_charges()
                    if verbose:
                        self._print_rated_transactions_summary()

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
            Q(orderpackages__prepaid_package__status=PackageStatus.ACTIVE.value)
        ).prefetch_related(
            'orderpackages_set__prepaid_package',
            'orderprice_set',
            'orderservice_set__service'
        ).order_by('start_date', 'order_id').distinct()
        self.orders_data = list(orders)

    def _validate_orders_data(self) -> None:
        """
        Validates the loaded orders data to ensure there are no conflicts, such as duplicate services across active
        orders. Sets the 'data_validated' flag based on the outcome of the validation.
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
        This step prepares the transaction processors needed for the rating process.
        """

        self.transaction_processors.clear()
        if not self.orders_data:
            logger.warning(f'No orders data for client {self.client.pk}')
        else:
            logger.info('Adding transaction processors')
            for order in self.orders_data:
                get_transaction_processors(order, processors_list=self.transaction_processors)

    def _load_transactions(self) -> None:
        """
        Loads transactions for the client within the rating period.

        Filters transactions by vendor client and timestamp, sorting and preparing them for processing.

        Raises:
            Exception: For any exceptions that occur during the loading of transactions.
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
                logger.warning(f'No UsageTransactions to load for client {self.client.pk}')

        except Exception as e:
            logger.error(f'Error: {e}')

    def _rate_transactions(self) -> None:
        """
        Processes each transaction, determining which charge object (if any) should be applied.

        Unprocessable transactions are moved to the 'skipped_transactions' queue.
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

    def _save_charges(self) -> None:
        """
        Saves the calculated charges to the database.

        This includes charges for orders, prepaid packages, and invoices, applying any necessary updates or
        deletions before saving new records.
        """

        logger.info(f'Saving order charges')

        with transaction.atomic():
            logger.debug(f'... deleting pending charge records')
            OrderCharge.objects.filter(
                vendor__client=self.client,
                period=self.charge_date
            ).delete()

            logger.debug(f'... saving charges')
            for processor in self.transaction_processors:
                processor.save_charges(self.charge_date)

    def _print_rated_transactions_summary(self):
        """
        (Optional) Prints a summary of the transactions processed by each transaction processor.

        This method is intended for debugging or reporting purposes and may not be used in production environments.
        """
        for processor in self.transaction_processors:
            print(processor.transactions_summary)
