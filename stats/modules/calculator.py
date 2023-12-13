from vendors.models import VendorService
from shared.modules import InputFilesMixin, ServiceUsageMixin, MappedTransactions
from services.modules import FiltersMixin
from ..models import UsageStats, Vendor

from typing import Tuple, Union
from collections import namedtuple
from pandas import DataFrame
import logging

ServiceMappingResult = namedtuple("ServiceMappingResult", ["status", "data", "transactions", "all_rows_mapped"])
logger = logging.getLogger('et_billing.stats.usage_calculator')


class BaseServicesMapper(FiltersMixin, InputFilesMixin, ServiceUsageMixin):
    """ A helper class that calculates"""

    def map_service_usage(self, input_file, skip_status_five=True) -> Tuple[int, Union[None, MappedTransactions]]:
        """ Reads the input file and maps used services
            :returns namedtuple: (status: int, transactions: dataframe, is_reconciled: Boolean)
        """

        period, vendor_id = input_file.period, input_file.vendor_id
        logger.debug(f"Starting usage calcs for vendor {vendor_id} for {period}.")

        # Load dataframe and convert all numbers
        logger.debug(f"Loading transactions for vendor {vendor_id} for {period}.")
        df = self.load_data_for_service_usage(input_file.file.path, skip_status_five)  # FromInputMixin
        if df is None:
            logger.info(f'vendor_id: {vendor_id}, period_id: {period}, return: No transactions')
            return 3, None

        # Load service filter groups
        service_filters = self.load_vendor_service_filters(vendor_id)  # From FilterMixin
        if service_filters is None:
            logger.info(f'vendor_id: {vendor_id}, period_id {period}, return: No services configured')
            return 1, None

        # Map vendor services to dataframe
        logger.debug("Calculating transaction based stats")
        mapped_data = self.map_transactions(df, service_filters)  # from ServiceUsageMixin
        return 0, mapped_data


class ServiceUsageCalculator(BaseServicesMapper):
    """ A helper class that calculates used for calculation of service usage """

    _BIO_AUTH_SERVICE_ID = 50
    _LEGAL_PERSONS_SERVICE_ID = 36
    _UNIQUE_USERS_SERVICE_ID = 32

    def save_service_usage_period_vendor(self, input_file, skip_status_five=True):
        """ Calculates and saves service usage """

        period, vendor_id = input_file.period, input_file.vendor_id

        # Load transactions and map vendor services
        status, mapped_data = self.map_service_usage(input_file, skip_status_five)
        if status != 0:
            return status

        # Update vendor status
        self._update_vendor_is_reconciled(vendor_id, mapped_data.fully_mapped)
        if not mapped_data.fully_mapped:
            logger.info(f'vendor_id: {vendor_id}, period_id: {period}, return : Not reconciled')
            return 4

        # Get transaction based stats
        df = mapped_data.dataframe
        res = df.service_id.value_counts()
        data = [(k, v) for k, v in res.items() if v is not None]

        # Update calculations for Legal Person eID (type 19)
        if data:
            for record in data:
                service_id, count = record
                if service_id == self._LEGAL_PERSONS_SERVICE_ID:
                    data.remove(record)
                    data.append((service_id, count // 2))
                    break

        # Get aggregation based stats
        if data and "Bio required" in df.columns:
            logger.debug("Calculating BioID stats")
            df_bio = df[df["Bio required"] == 'yes'][["ThreadID"]].copy()
            df_bio = df_bio.drop_duplicates()
            n = len(df_bio)
            if n > 0:
                data.append((self._BIO_AUTH_SERVICE_ID, n))

        # Add unique users where required
        if VendorService.objects.filter(vendor_id=vendor_id, service_id=32).exists():
            logger.debug("Calculating unique users stats")
            n = df["PID receiver"].dropna().nunique()
            if n > 0:
                data.append((self._UNIQUE_USERS_SERVICE_ID, n))

        # Save usage stats
        logger.debug("Saving usage stats")
        for el in data:
            service_id, unit_count = el
            self._save_service_usage(period, vendor_id, service_id, unit_count)
        logger.info(f'vendor_id: {vendor_id}, period_id: {period}, return : Complete')
        return 0

    @staticmethod
    def _update_vendor_is_reconciled(vendor_id, is_reconciled=False):
        """ Updates the reconciled status of a Vendor object """

        try:
            vendor = Vendor.objects.get(vendor_id=vendor_id)
            if vendor.is_reconciled != is_reconciled:
                logger.debug(f"Updating vendor is_reconciled - set status {is_reconciled}")
                vendor.is_reconciled = is_reconciled
                vendor.save()

        except Vendor.DoesNotExist:
            logger.warning(f"No vendor object with vendor_id {vendor_id}")

    @staticmethod
    def _save_service_usage(period: str, vendor_id: int, service_id: int, unit_count: int) -> None:
        """ Saves or updates service usage statistics. """

        try:
            usage = UsageStats.objects.get(period=period, vendor_id=vendor_id, service_id=service_id)
            if usage.unit_count != unit_count:
                usage.unit_count = unit_count
                usage.save()

        except UsageStats.DoesNotExist:
            usage = UsageStats.objects.create(
                period=period, vendor_id=vendor_id, service_id=service_id, unit_count=unit_count)
            usage.save()


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
