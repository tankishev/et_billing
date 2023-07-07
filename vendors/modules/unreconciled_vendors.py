# CODE OK
from services.modules import FiltersMixin
from services.models import Service
from shared.modules import ServiceUsageMixin
from .usage_calculator import ServiceUsageCalculator
from ..models import VendorInputFile

from datetime import datetime as dt
import logging


django_logger = logging.getLogger('vendors.unreconciled_vendors')


class TransactionMapper(FiltersMixin, ServiceUsageMixin):
    """ A simple class to map transactions to Service objects"""

    def __init__(self, df):
        self.df = df
        self.found_services = []
        self.map_services()

    def map_services(self) -> dict or None:
        services = self.load_all_service_filters()
        self.df, _ = self.calc_usage(self.df, services)
        found_ids = list(self.df.service_id.unique())
        for el in found_ids:
            service = Service.objects.get(service_id=el)
            self.found_services.append(str(service))


def get_vendor_unreconciled(file_id: int) -> dict:
    """ Returns a dict with unreconciled transactions and suggested service for them.
        Used for population of Unreconciled transactions modal.
    """

    django_logger.info(f"Mapping transactions for VendorInputFile pk {file_id}")
    start = dt.now()

    try:
        input_file = VendorInputFile.objects.get(id=file_id)
        calc = ServiceUsageCalculator()
        res = calc.find_unreconciled_transactions(input_file)
        mapper = TransactionMapper(res)

        return {
            'table_values': mapper.df.values.tolist(),
            'services': mapper.found_services
        }

    except VendorInputFile.DoesNotExist:
        django_logger.warning(f"No VendorInputFile with id {file_id}")

    finally:
        execution_time = dt.now() - start
        django_logger.info(f"Execution time: {execution_time}")
