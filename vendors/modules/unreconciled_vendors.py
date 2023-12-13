from services.models import Service
from stats.modules.calculator import BaseServicesMapper
from ..models import VendorInputFile

from datetime import datetime as dt
from pandas import DataFrame
import logging


django_logger = logging.getLogger('vendors.unreconciled_vendors')


class UnreconciledTransactionsMapper(BaseServicesMapper):
    """ A helper class that finds not configured service usage """

    def map(self, input_file, skip_status_five=True) -> DataFrame:
        """ Finds service usage which cannot be mapped to vendor service configuration and guesses the service.
        """

        # Load input_file/s and map services
        _, mapped_data = self.map_service_usage(input_file, skip_status_five)
        df = mapped_data.dataframe

        # Drop mapped rows and guess unmapped ones
        unmapped_df = df[df['service_id'].isna()][['Type', 'Status', 'Signing type', 'Cost']].drop_duplicates().copy()
        service_filters = self.load_all_service_filters()
        mapped_data = self.map_transactions(unmapped_df, service_filters)

        return mapped_data.dataframe


def get_vendor_unreconciled(file_id: int) -> dict:
    """ Returns a dict with unreconciled transactions and suggested service for them.
        Used for population of Unreconciled transactions modal.
    """

    django_logger.info(f"Mapping transactions for VendorInputFile pk {file_id}")
    start = dt.now()

    try:
        input_file = VendorInputFile.objects.get(id=file_id)
        mapper = UnreconciledTransactionsMapper()

        data = mapper.map(input_file)
        found_ids = list(data.service_id.unique())
        found_services = [str(el) for el in Service.objects.filter(service_id__in=found_ids)]
        return {
            'table_values': data.values.tolist(),
            'services': found_services
        }

    except VendorInputFile.DoesNotExist:
        django_logger.warning(f"No VendorInputFile with id {file_id}")

    finally:
        execution_time = dt.now() - start
        django_logger.info(f"Execution time: {execution_time}")
