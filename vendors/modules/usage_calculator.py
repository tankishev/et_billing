# CODE OK
from services.modules import FiltersMixin
from stats.modules import save_service_usage
from .input_files import InputFilesMixin
from .service_usage import ServiceUsageMixin
from ..models import Vendor, VendorService

import logging

logger = logging.getLogger('et_billing.vendors.usage_calculator')


class ServiceUsageCalculator(FiltersMixin, ServiceUsageMixin, InputFilesMixin):
    """ A helper class that calculates and save vendor service usage """

    def find_unreconciled_transactions(self, input_file, skip_status_five=True):
        """ Provides a summary of unreconciled transactions """

        _, df, _ = self._calculate_service_usage(input_file, skip_status_five)
        return df[df['service_id'].isna()][['Type', 'Status', 'Signing type', 'Cost']].drop_duplicates().copy()

    def save_service_usage_period_vendor(self, input_file, skip_status_five=True):
        """ Calculates and saves service usage """

        period, vendor_id = input_file.period, input_file.vendor_id

        # Calculate vendor service usage
        res, df, is_reconciled = self._calculate_service_usage(input_file, skip_status_five)
        if res != 0:
            return res

        # Update vendor status
        self.update_vendor_is_reconciled(vendor_id, is_reconciled)
        if not is_reconciled:
            logger.info(f'vendor_id: {vendor_id}, period_id: {period}, return : Not reconciled')
            return 4

        # Get transaction based stats
        res = df.service_id.value_counts()
        data = [(k, v) for k, v in res.items() if v is not None]

        # Get aggregation based stats
        if data and "Bio required" in df.columns:
            logger.debug("Calculating BioID stats")
            df_bio = df[df["Bio required"] == 'yes'][["ThreadID"]].copy()
            df_bio = df_bio.drop_duplicates()
            n = len(df_bio)
            if n > 0:
                data.append((50, n))

        # Add unique users where enabled requiring enablement
        if VendorService.objects.filter(vendor_id=vendor_id, service_id=32).exists():
            logger.debug("Calculating unique users stats")
            n = df["PID receiver"].dropna().nunique()
            if n > 0:
                data.append((32, n))

        # Save usage stats
        logger.debug("Saving usage stats")
        for el in data:
            service_id, unit_count = el
            save_service_usage(period, vendor_id, service_id, unit_count)
        logger.info(f'vendor_id: {vendor_id}, period_id: {period}, return : Complete')
        return 0

    @staticmethod
    def update_vendor_is_reconciled(vendor_id, is_reconciled=False):
        """ Updates the reconciled status of a Vendor object """

        try:
            vendor = Vendor.objects.get(vendor_id=vendor_id)
            if vendor.is_reconciled != is_reconciled:
                logger.debug(f"Updating vendor is_reconciled - set status {is_reconciled}")
                vendor.is_reconciled = is_reconciled
                vendor.save()

        except Vendor.DoesNotExist:
            logger.warning(f"No vendor object with vendor_id {vendor_id}")

    def _calculate_service_usage(self, input_file, skip_status_five=True):
        """ Reads the input file and calculates service usage """

        period, vendor_id = input_file.period, input_file.vendor_id
        logger.debug(f"Starting usage calcs for vendor {vendor_id} for {period}.")

        # Load dataframe and convert all numbers
        logger.debug(f"Loading transactions for vendor {vendor_id} for {period}.")
        df = self.load_data_for_service_usage(input_file.file.path, skip_status_five)
        if df is None:
            logger.info(f'vendor_id: {vendor_id}, period_id: {period}, return: No transactions')
            return 3, None, None

        # Load service filters
        service_filters = self.get_service_filters()
        services = self.load_vendor_service_filters(vendor_id, service_filters)
        if services is None:
            logger.info(f'vendor_id: {vendor_id}, period_id {period}, return: No services configured')
            return 1, None, None

        # Calculate transaction based services
        logger.debug("Calculating transaction based stats")
        df, is_reconciled = self.calc_usage(df, services)
        return 0, df, is_reconciled