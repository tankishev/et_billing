from typing import List, Optional
from vendors.models import VendorService
import logging

logger = logging.getLogger(f'et_billing.{__name__}')


class RatedTransaction:
    """
    This class represents a transaction that needs to be rated.

    Attributes:
        TRANSACTION_STATUS_FAILED (int): Constant representing the failed transaction status.
        transaction (UsageTransaction): The transaction instance.
        bio_pin (bool): Was there BioID service associated with the transaction.
        service_id (int): ID of the service involved in the transaction.
        thread_id (int): ID of the thread associated with the transaction.
        vendor_id (int): ID of the vendor involved in the transaction.
        vs_id (Optional[int]): ID of the VendorService, initialized as None.
        charge (float): The charge amount for the transaction, initialized to 0.
    """

    TRANSACTION_STATUS_FAILED = 5

    def __init__(self, transaction) -> None:
        self.transaction = transaction
        self.bio_pin = transaction.bio_pin
        self.service_id = transaction.service_id
        self.thread_id = transaction.thread_id
        self.vendor_id = transaction.vendor_id
        self.vs_id: Optional[int] = None
        self.charge = 0

    def set_vs(self, vs_list: List[VendorService]) -> None:
        """
        Sets the VendorService ID for the transaction based on a list of VendorServices.
        :param vs_list: A list of VendorService objects to search through.
        """

        try:
            if self.transaction.transaction_status_id != self.TRANSACTION_STATUS_FAILED:
                vs_id = next((vendor_service.id for vendor_service in vs_list
                              if vendor_service.vendor_id == self.vendor_id
                              and vendor_service.service_id == self.service_id), None)
                if vs_id:
                    self.vs_id = vs_id
                else:
                    logger.warning(f'Mapped transaction without VendorService. '
                                   f'account: {self.vendor_id}. service {self.service_id}')

        except Exception as e:
            logger.error(f'Error: {e}')
            raise

    def __str__(self):
        timestamp = self.transaction.timestamp
        return f'{timestamp.strftime("%Y-%m-%d")}-account {self.vendor_id}-service {self.service_id}-cost {self.charge}'
