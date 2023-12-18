from stats.modules.calculator import BaseServicesMapper
from ..models import RatedTransaction
from vendors.models import Vendor, VendorService
from services.models import Service
from contracts.models import OrderService, Client


class RatingCalculator(BaseServicesMapper):
    """ A helper class use to map services rate and store transactions """

    _PRO_SIGN_VENDORS = [52]

    def __init__(self):
        self.transactions = []
        self.vendor = None
        self.client = None
        self.service_costs = None

    def load_transactions(self, input_file):

        # Set globals
        self._set_globals(input_file.vendor)

        # Load data and map vendor services
        status, mapped_data = self.map_service_usage(input_file)
        if status != 0:
            return status

        # Save transactions
        for transaction in mapped_data.transactions:
            charge_user = transaction.payer == 'Client'
            print('\n'.join(str(el) for el in [
                transaction.date_created,
                self.client,
                self.vendor,
                transaction.service_id,
                self._get_service_cost(transaction.service_id),
                charge_user
            ]))
            # rated_transaction = RatedTransaction(
            #     timestamp=transaction.date_created,
            #     client=self._get_client(),
            #     vendor=self.vendor,
            #     service=transaction.service,
            #     cost=self._get_service_cost(transaction.service),
            #     charge_user=transaction.payer
            # )

    def _set_globals(self, vendor):
        self.vendor = vendor
        self.client = self._get_client()
        self.transactions.clear()
        self.service_costs = self._get_service_costs()

    def _get_client(self):
        if self.vendor.vendor_id in self._PRO_SIGN_VENDORS:
            return Client.objects.get(pk=0)
        return self.vendor.client

    def _get_service_costs(self):
        os = OrderService.objects.filter(
            order__contract__client=self.client,
            order__is_active=True,
            order__contract__is_active=True
        )

