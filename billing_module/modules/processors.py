from abc import ABC, abstractmethod
from contracts.models import Order
from .transaction import RatedTransaction
from .utils import ChargeType
from ..models import PrepaidPackage
import logging

logger = logging.getLogger(f'et_billing.{__name__}')


class BaseTransactionProcessor(ABC):
    """
    Abstract base class for transaction processing and charge recording related to various services.

    Attributes:
        BIO_PIN_SERVICE_ID (int): Service ID for bio pin service.
        LEGAL_ENTITIES_SERVICE_ID (int): Service ID for legal entities eID service.
        order (Order): Associated Order object.
        vs_list (set[int]): Set of VendorService IDs linked to the order.
        prices (dict[int, float]): Mapping of service IDs to unit prices.
        charge_type (ChargeType): Type of charge applied.
        transactions (list[Transaction]): List to store transaction records.
        service_charges (dict[int, dict]): Stores service charges keyed by vendor ID.

    Methods:
        __init__: Initializes a new instance with an order and charge type.
        charges_summary: Returns a summary of charges for all services.
        total_charges: Calculates the total charges incurred.
        process_transaction: Abstract method for processing a transaction.
        _add_service_charge: Records a charge for a given service and vendor.
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
    def charges_summary(self) -> str:
        """
        Summarizes the charges for all services included in the order.

        :return: A formatted string summarizing the total counts and charges per service, along with the overall totals.
        """

        summary = dict()
        for service_dict in self.service_charges.values():
            for service_id, charges in service_dict.items():
                summary_item = summary.setdefault(service_id, {'count': 0, 'charge': 0})
                summary_item['count'] += charges['count']
                summary_item['charge'] += charges['charge']

        retval = f'Order {self.order.order_id}; ' \
                 f'Validity: {self.order.start_date} - {self.order.end_date}; ' \
                 f'Charge type: {self.charge_type}; ' \
                 f'Transactions: {sum(el["count"] for el in summary.values())}; ' \
                 f'Charge: {sum(el["charge"] for el in summary.values())}'

        balance = self.__dict__.get('balance', None)
        if balance:
            retval += f'; Balance: {balance}'

        for k, v in summary.items():
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


class NoChargeTransactionProcessor(BaseTransactionProcessor):
    """
    Abstract base class for handling charge data.
    """

    def __init__(self, order: Order) -> None:
        """
        Initializes a NoChargeTransactionProcessor instance with an order.

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


class ChargeableTransactionProcessor(BaseTransactionProcessor):
    """
    Processor for transactions that involve chargeable services.

    Attributes:
        _processed_bio_threads (set[int]): Tracks processed bio pin service threads.
        _processed_legal_threads (set[int]): Tracks processed legal entities service threads.

    Methods:
        __init__: Initializes a new instance with chargeable transactions.
        process_transaction: Processes a transaction and applies charges if necessary.
        _calculate_transaction_charges: Calculates charges for a given transaction.
        _meets_charging_criteria: Abstract method to check if transaction meets charging criteria.
        _process_transaction: Applies charges and updates service charges for a transaction.
        _post_transaction_processing: Abstract method for post-transaction operations.
    """

    def __init__(self, order: Order, charge_type: ChargeType) -> None:
        """
        Initializes a ChargeableTransactionProcessor instance with an order and a charge type.

        :param order: The Order object associated with the processor.
        :param charge_type: The type of charge to be processed.
        """

        super().__init__(order, charge_type)
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
        __init__: Initializes a new instance for invoice transactions.
        _meets_charging_criteria: Determines if a transaction meets criteria for invoicing.
    """

    def __init__(self, order: Order, enforce_end_date=False) -> None:
        """
        Initializes an InvoiceTransactionProcessor instance.

        :param order: The Order object associated with the charge.
        :param enforce_end_date: If True, enforces transaction processing only before the order end date.
        """

        super().__init__(order, ChargeType.INVOICE)
        self.enforce_end_date = enforce_end_date

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


class PrepaidTransactionProcessor(ChargeableTransactionProcessor):
    """
    Processor for handling prepaid transactions.

    Attributes:
        prepaid_package (PrepaidPackage): The associated prepaid package.
        balance (float): Current balance of the prepaid package.

    Methods:
        __init__: Initializes a new instance with a prepaid package.
        _meets_charging_criteria: Determines if a transaction meets criteria based on package balance.
        _post_transaction_processing: Operations after updating a transaction and storing its charge.
    """

    def __init__(self, order: Order, package: PrepaidPackage) -> None:
        """
        Initializes a PrepaidTransactionProcessor instance with an order and prepaid package.

        :param order: The Order object associated with the charge.
        :param package: The PrepaidPackage associated with the order.
        """

        super().__init__(order, ChargeType.PREPAID)
        self.prepaid_package = package
        self.balance = package.available_balance

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

        self.balance -= transaction.charge


def add_transaction_processor(order: Order, **kwargs):
    """
    Adds appropriate transaction processors to a list based on the payment type of the order.

    This function examines the payment type of the given order and appends the corresponding
    transaction processor(s) to a list of processors. The list of processors can be optionally
    passed in via `kwargs`. If no list is provided, a new one is created. The function supports
    handling of 'NO_CHARGE', 'PREPAID', 'PREPAID_SHARED', and 'INVOICE' payment types.

    Parameters:
    - order (Order): The order for which transaction processors are to be added.
    - **kwargs: Optional keyword arguments. Can include 'processors_list', a list to which
                transaction processors will be added. If not provided, a new list is created.

    Returns:
    - List[ChargeableTransactionProcessor]: A list of transaction processor instances.

    Raises:
    - ValueError: If an unknown payment type is encountered or other value-related errors occur.

    Note:
    - For 'PREPAID' and 'PREPAID_SHARED' payment types, a processor is added for each associated
      prepaid package. Additionally, if the order has no end date, an 'InvoiceTransactionProcessor'
      is added.
    - For 'INVOICE' payment types, an 'InvoiceTransactionProcessor' with 'enforce_end_date' set to
      True is always added.
    """

    try:
        payment_type = ChargeType(order.payment_type_id)
        processors_list = kwargs.get('processors_list', [])

        if payment_type == ChargeType.NO_CHARGE:
            processors_list.append(NoChargeTransactionProcessor(order))

        elif payment_type in (ChargeType.PREPAID, ChargeType.PREPAID_SHARED):
            for order_package in order.orderpackages_set.all():
                prepaid_package = order_package.prepaid_package
                processors_list.append(PrepaidTransactionProcessor(order, prepaid_package))
            if order.end_date is None:
                processors_list.append(InvoiceTransactionProcessor(order))

        elif payment_type == ChargeType.INVOICE:
            processors_list.append(InvoiceTransactionProcessor(order, enforce_end_date=True))

        return processors_list

    except ValueError as err:
        logger.error(f'Error: {err}')
        raise
