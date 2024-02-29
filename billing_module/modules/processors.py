from abc import ABC, abstractmethod
from contracts.models import Order
from .packages import renew_package
from .transaction import RatedTransaction
from .utils import ChargeType, ChargeStatus
from ..models import PrepaidPackage, Invoice, PrepaidPackageCharge, OrderCharge
import logging

logger = logging.getLogger(f'et_billing.{__name__}')


class BaseTransactionProcessor(ABC):
    """
    Serves as an abstract base class for transaction processing and charge recording related to various services.

    Attributes:
        BIO_PIN_SERVICE_ID (int): Identifier for the bio pin service.
        LEGAL_ENTITIES_SERVICE_ID (int): Identifier for the legal entities eID service.
        order (Order): The associated Order instance.
        vs_list (set[int]): Collection of VendorService IDs linked to the order.
        prices (dict[int, float]): Mapping of service IDs to their respective unit prices.
        charge_type (ChargeType): The type of charge to be applied.
        transactions (list[Transaction]): Container for storing processed transaction records.
        service_charges (dict[int, dict]): Nested dictionary holding service charges, keyed by vendor ID and service ID.

    Methods:
        transactions_summary: Property that provides a summary of all processed transactions and their charges.
        total_charges: Property that calculates the total charges accumulated from processed transactions.
        process_transaction(transaction): Abstract method to process a given transaction.
        save_charges(period): Abstract method to be implemented by subclasses for saving calculated charges.
        _add_service_charge(vendor_id, service_id, charge): Helper method to record a service charge.
        _aggregate_charges(): Helper method to aggregate charges from all processed transactions.
    """

    BIO_PIN_SERVICE_ID = 50
    LEGAL_ENTITIES_SERVICE_ID = 36

    def __init__(self, order: Order, charge_type: ChargeType) -> None:
        """
        Initializes a new BaseTransactionProcessor instance.

        :param order: The Order object associated with the charge.
        :param charge_type: The type of charge to be processed.
        """

        self.order = order
        self.vs_list = set(order_service.service.id for order_service in self.order.orderservice_set.all())
        self.prices = {op.service_id: op.unit_price for op in self.order.orderprice_set.all()}
        self.charge_type = charge_type

        # Data stores
        self.transactions = []
        self.service_charges = dict()

    @property
    def transactions_summary(self) -> str:
        """
        Summarizes the charges for all services included in the order.

        :return: A formatted string summarizing the total counts and charges per service, along with the overall totals.
        """

        charges_summary = self._aggregate_charges()
        retval = f'Order {self.order.order_id}; ' \
                 f'Validity: {self.order.start_date} - {self.order.end_date}; ' \
                 f'Charge type: {self.charge_type}; ' \
                 f'Transactions: {sum(el["count"] for el in charges_summary.values())}; ' \
                 f'Charge: {sum(el["charge"] for el in charges_summary.values())}'

        balance = self.__dict__.get('balance', None)
        if balance:
            retval += f'; Balance: {balance}'

        for k, v in charges_summary.items():
            retval += f'\n\tService {k}: count {v["count"]}; charge {v["charge"]}'
        return retval

    @property
    def total_charges(self) -> float:
        """
        Calculates the total charges for all services.

        :return: The sum of all charges as a float. Returns 0 if there are no service charges.
        """

        if self.service_charges:
            total_charges = 0
            for service_charges in self.service_charges.values():
                for charges in service_charges.values():
                    total_charges += charges['charge']
            return total_charges
        return 0

    @abstractmethod
    def process_transaction(self, transaction: RatedTransaction) -> bool:
        """
        Abstract method to process a given transaction. Must be implemented in subclasses.

        :param transaction: The RatedTransaction object to be processed.
        :return: Boolean indicating whether the transaction was processed successfully.
        """

        pass

    @abstractmethod
    def save_charges(self, charge_date):
        pass

    def _add_service_charge(self, vendor_id, service_id, charge: float) -> None:
        """
        Records the charge for a service for a given account number.

        :param vendor_id: ID of the account number.
        :param service_id: ID of the provided service.
        :param charge: The charge for the service.
        """

        vendor_charges = self.service_charges.setdefault(vendor_id, {})
        service = vendor_charges.setdefault(service_id, {'count': 0, 'charge': 0})
        service['count'] += 1
        service['charge'] += charge

    def _aggregate_charges(self) -> dict:
        """
        Aggregates the total charges for all services.

        :return: Dictionary with aggregated count and charge values keyed by service_id.
        """

        charges_summary = dict()
        for service_dict in self.service_charges.values():
            for service_id, charges in service_dict.items():
                summary_item = charges_summary.setdefault(service_id, {'count': 0, 'charge': 0})
                summary_item['count'] += charges['count']
                summary_item['charge'] += charges['charge']
        return charges_summary

    def _save_order_charges(self, charge_date) -> None:

        # Generate list of charges
        order_charges = []
        for vendor_id, service_charges in self.service_charges.items():
            for service_id, charge_data in service_charges.items():
                unit_count = charge_data.get('count', 0)
                charge_amount = charge_data.get('charge', 0)
                order_charges.append(
                    OrderCharge(
                        period=charge_date,
                        order=self.order,
                        payment_type_id=self.charge_type.value,
                        vendor_id=vendor_id,
                        service_id=service_id,
                        service_count=unit_count,
                        charged_units=charge_amount
                    )
                )

        if order_charges:
            OrderCharge.objects.bulk_create(order_charges)


class NoChargeTransactionProcessor(BaseTransactionProcessor):
    """
    A processor to handle transactions that do not incur any charges.
    """

    def __init__(self, order: Order) -> None:
        """
        Initializes a NoChargeTransactionProcessor instance with an order, setting the charge type to NO_CHARGE.

        :param order: The Order object associated with the processor.
        """

        super().__init__(order, ChargeType.NO_CHARGE)

    def process_transaction(self, transaction: RatedTransaction) -> bool:
        """
        Processes a given transaction without incurring any charges.

        :param transaction: The RatedTransaction object to be processed.
        :return: True if the transaction is successfully processed, False otherwise.
        """

        if transaction.vs_id in self.vs_list:
            self._add_service_charge(transaction.vendor_id, transaction.service_id, 0)
            self.transactions.append(transaction)
            return True
        return False

    def save_charges(self, charge_date):
        if self.transactions:
            self._save_order_charges(charge_date)


class ChargeableTransactionProcessor(BaseTransactionProcessor):
    """
    Extends the base processor abstract class for processors that handle chargeable transactions.

    Attributes:
        _processed_bio_threads (set[int]): Tracks processed bio pin service threads.
        _processed_legal_threads (set[int]): Tracks processed legal entities service threads.
        provisional (bool): Indicates whether the processor is provisional. Provisional processors are created to
            process transactions that overflow the outstanding balance of existing prepaid packages.

    Methods:
        process_transaction(transaction): Processes the given transaction.
        _calculate_transaction_charges(transaction): Calculates the charges for a given transaction based.
        _meets_charging_criteria(**kwargs): Abstract method defining criteria if a transaction is eligible for charging.
        _process_transaction(transaction, charges): Applies the calculated charges to the transaction.
        _post_transaction_processing(**kwargs): Abstract method for any additional operations after processing.
    """

    def __init__(self, order: Order, charge_type: ChargeType, provisional=False) -> None:
        """
        Initializes a ChargeableTransactionProcessor instance with an order and a charge type.

        :param order: The Order object associated with the processor.
        :param charge_type: The type of charge to be processed.
        :param provisional: Marks the processor as provisional. Defaults to False.
        """

        super().__init__(order, charge_type)
        self.provisional = provisional
        self._processed_bio_threads = set()
        self._processed_legal_threads = set()

    def process_transaction(self, transaction: RatedTransaction) -> bool:
        """
        Processes a given transaction and records the charge if applicable.

        :param transaction: The RatedTransaction object to be processed.
        :return: True if the transaction is successfully processed and meets charging criteria, False otherwise.
        """

        if transaction.vs_id in self.vs_list:
            transaction_charges = self._calculate_transaction_charges(transaction)
            if self._meets_charging_criteria(transaction=transaction, charges=transaction_charges):
                self._process_transaction(transaction, transaction_charges)
                self._post_transaction_processing(transaction=transaction)
                return True
        return False

    def _calculate_transaction_charges(self, transaction: RatedTransaction) -> dict:
        """
        Calculates the charges for a given transaction based on service ID and thread ID.

        :param transaction: The RatedTransaction object for which charges are being calculated.
        :return: A dictionary with calculated charges.
        """

        service_id, thread_id = transaction.service_id, transaction.thread_id
        if service_id == self.LEGAL_ENTITIES_SERVICE_ID and thread_id in self._processed_legal_threads:
            return {}

        charges = {'service_charge': self.prices.get(service_id, 0)}
        if service_id == self.LEGAL_ENTITIES_SERVICE_ID:
            self._processed_legal_threads.add(thread_id)
        if transaction.bio_pin and thread_id not in self._processed_bio_threads:
            charges.update({'bio_pin': self.prices.get(self.BIO_PIN_SERVICE_ID, 0)})
            self._processed_bio_threads.add(thread_id)

        return charges

    @abstractmethod
    def _meets_charging_criteria(self, **kwargs) -> bool:
        """
        Determines if a transaction meets the charging criteria. Abstract method to be implemented in subclasses.

        :return: True if the transaction meets charging criteria, False otherwise.
        """
        pass

    def _process_transaction(self, transaction: RatedTransaction, charges: dict) -> None:
        """
        Processes a transaction by adding the charge and updating service charges.

        :param transaction: The RatedTransaction object to process.
        :param charges: A dictionary of charges related to the transaction.
        """

        vendor_id, service_id = transaction.vendor_id, transaction.service_id
        service_charge = charges.get('service_charge', None)
        if service_charge is not None:
            transaction.charge = service_charge
            self._add_service_charge(vendor_id, service_id, service_charge)

        bio_pin_charge = charges.get('bio_pin', None)
        if bio_pin_charge is not None:
            self._add_service_charge(vendor_id, self.BIO_PIN_SERVICE_ID, bio_pin_charge)

        self.transactions.append(transaction)

    def _post_transaction_processing(self, **kwargs) -> None:
        """
        Abstract method for operations to be executed after a transaction is processed. To be implemented in subclasses.
        """

        pass


class InvoiceTransactionProcessor(ChargeableTransactionProcessor):
    """
    Processor for transactions that are to be invoiced.

    Attributes:
        enforce_end_date (bool): Flag to enforce transaction processing within order end date.

    Methods:
        save_charges(period): Implements saving of charge details in an Invoice object for the processed transactions.
        _meets_charging_criteria: Determines if a transaction meets criteria for invoicing.
    """

    def __init__(self, order: Order, enforce_end_date=False, **kwargs) -> None:
        """
        Initializes an InvoiceTransactionProcessor instance.

        :param order: The Order object associated with the charge.
        :param enforce_end_date: If True, enforces transaction processing only before the order end date.
        """

        super().__init__(order, ChargeType.INVOICE, **kwargs)
        self.enforce_end_date = enforce_end_date

    def save_charges(self, charge_date) -> None:
        """
        Implements saving of charge details in an Invoice object for the processed transactions.

        :param charge_date: Charge_date for which the invoice needs to be created
        """
        if self.transactions:
            self._save_order_charges(charge_date)

            Invoice.objects.filter(
                order=self.order,
                charge_status_id=ChargeStatus.PENDING.value,
                period=charge_date
            ).delete()

            Invoice.objects.create(
                period=charge_date,
                order=self.order,
                ccy_type=self.order.ccy_type,
                charged_units=self.total_charges,
                charge_status_id=ChargeStatus.PENDING.value
            )

    def _meets_charging_criteria(self, **kwargs) -> bool:
        """
        Determines if a transaction meets the charging criteria for invoicing.

        :param kwargs: Keyword arguments including the transaction details.
        :return: True if the transaction meets the criteria for invoicing, False otherwise.
        """

        transaction = kwargs.get('transaction')
        if transaction is None:
            logger.error('Error: Expected key word argument "charges" not found')
            return False

        transaction_date = transaction.transaction.timestamp.date()
        return (
                self.order.end_date is None or
                self.enforce_end_date is False or
                transaction_date < self.order.end_date
        )


class PrepaidPackageProcessor(ChargeableTransactionProcessor):
    """
    Processor for handling orders with prepaid amounts.

    Attributes:
        prepaid_package (PrepaidPackage): The associated prepaid package.
        balance (float): Current balance of the prepaid package.

    Methods:
        save_charges(period): Implements saving of a PrepaidPackageCharge for the processed transactions.
        _activate_new_package(activation_date): Adds new prepaid package to the processor.
        _meets_charging_criteria: Determines if a transaction meets criteria based on package balance.
        _post_transaction_processing: Operations after updating a transaction and storing its charge.
    """

    def __init__(self, order: Order, package: PrepaidPackage, **kwargs) -> None:
        """
        Initializes a PrepaidPackageProcessor instance with an order and prepaid package.

        :param order: The Order object associated with the charge.
        :param package: The PrepaidAmountPackage associated with the order.
        """

        super().__init__(order, ChargeType.PREPAID_PACKAGE, **kwargs)
        self.prepaid_package = package
        self.balance = package.available_balance

    def save_charges(self, charge_date) -> None:
        """
        Saves a PrepaidPackageCharge for the processed transactions.

        :param charge_date: charge_date for which to save the charge.
        """

        if self.transactions:
            self._save_order_charges(charge_date)

            PrepaidPackageCharge.objects.filter(
                prepaid_package__orderpackages__order=self.order,
                charge_status_id=ChargeStatus.PENDING.value,
                charge_date=charge_date
            ).delete()

            PrepaidPackageCharge.objects.create(
                charge_date=charge_date,
                charged_units=self.total_charges,
                prepaid_package=self.prepaid_package,
                charge_status_id=ChargeStatus.PENDING.value
            )

    def _activate_new_package(self, activation_date):
        """
        Creates a new prepaid package to extend the one associated with the processor.

        :param activation_date:
        """
        new_package = renew_package(self.prepaid_package, activation_date)
        self.prepaid_package = new_package
        self.balance = self.prepaid_package.balance

    def _meets_charging_criteria(self, **kwargs) -> bool:
        """
        Determines if a transaction meets the charging criteria for a prepaid package.

        :param kwargs: Keyword arguments including the charges details.
        :return: True if the transaction meets criteria based on package balance, False otherwise.
        """

        charges = kwargs.get('charges')
        if charges:
            total_charges = sum(v for v in charges.values())
            return total_charges <= self.balance

        logger.error('Error: Expected key word argument "charges" not found')
        return False

    def _post_transaction_processing(self, **kwargs) -> None:
        """
        Executes operations after a transaction is updated and its charge is stored.

        :param kwargs: Keyword arguments including transaction details.
        """

        transaction = kwargs.get('transaction')
        if transaction is None:
            logger.error('Error: Expected keyword argument "transaction" not found')
            raise ValueError('Expected keyword argument "transaction" not found')

        # Activate new package if the processor was provisional
        if self.provisional:
            self._activate_new_package(transaction.date)
        self.balance -= transaction.charge


def get_transaction_processors(order: Order, **kwargs) -> list:
    """
    Adds appropriate transaction processors to a list based on the payment type of the order.

    This function examines the payment type of the given order and appends the corresponding
    transaction processor(s) to a list of processors. The list of processors can be optionally
    passed in via `kwargs`. If no list is provided, a new one is created. The function supports
    handling of 'NO_CHARGE', 'PREPAID_PACKAGE', 'PREPAID_SHARED', and 'INVOICE' payment types.

    Parameters:
    - order (Order): The order for which transaction processors are to be added.
    - **kwargs: Optional keyword arguments. Can include 'processors_list', a list to which
                transaction processors will be added. If not provided, a new list is created.

    Returns:
    - List[ChargeableTransactionProcessor]: A list of transaction processor instances.

    Raises:
    - ValueError: If an unknown payment type is encountered or other value-related errors occur.

    Note:
    - For 'PREPAID_PACKAGE' and 'PREPAID_SHARED' payment types, a processor is added for each associated
      prepaid package. Additionally, if the order has no end date, an 'InvoiceTransactionProcessor'
      is added.
    - For 'INVOICE' payment types, an 'InvoiceTransactionProcessor' with 'enforce_end_date' set to
      True is always added.
    """

    try:
        payment_type = ChargeType(order.payment_type_id)
        processors_list = kwargs.get('processors_list', [])

        if payment_type in (ChargeType.NO_CHARGE, ChargeType.SUBSCRIPTION):
            processors_list.append(NoChargeTransactionProcessor(order))

        elif payment_type in (ChargeType.PREPAID_PACKAGE, ChargeType.PREPAID_SHARED):
            for order_package in order.orderpackages_set.all():
                prepaid_package = order_package.prepaid_package
                processors_list.append(PrepaidPackageProcessor(order, prepaid_package))
                if package_renewable(prepaid_package):
                    processors_list.append(PrepaidPackageProcessor(order, prepaid_package, provisional=True))

            if order.end_date is None:
                processors_list.append(InvoiceTransactionProcessor(order, provisional=True))

        elif payment_type == ChargeType.INVOICE:
            processors_list.append(InvoiceTransactionProcessor(order, enforce_end_date=True))

        return processors_list

    except ValueError as err:
        logger.error(f'Error: {err}')
        raise


def package_renewable(package):
    """ temp blocker for functionality for package renewal"""
    return False
