# CODE OK
from services.modules import FiltersMixin
from .input_files import InputFilesMixin
from .service_usage import ServiceUsageMixin

import logging

logger = logging.getLogger('et_billing.shared.usage_calculator')


class BaseServiceUsageCalculator(FiltersMixin, ServiceUsageMixin, InputFilesMixin):
    """ A helper class that calculates"""

    def _calculate_service_usage(self, input_file, skip_status_five=True):
        """ Reads the input file and calculates service usage
            :returns tuple: (status: int, transactions: dataframe, is_reconciled: Boolean)
        """

        period, vendor_id = input_file.period, input_file.vendor_id
        logger.debug(f"Starting usage calcs for vendor {vendor_id} for {period}.")

        # Load dataframe and convert all numbers
        logger.debug(f"Loading transactions for vendor {vendor_id} for {period}.")
        df = self.load_data_for_service_usage(input_file.file.path, skip_status_five)  # FromInputMixin
        if df is None:
            logger.info(f'vendor_id: {vendor_id}, period_id: {period}, return: No transactions')
            return 3, None, None

        # Load service filters
        service_filters = self.get_service_filters()  # From FilterMixin
        services = self.load_vendor_service_filters(vendor_id, service_filters)  # From FilterMixin
        if services is None:
            logger.info(f'vendor_id: {vendor_id}, period_id {period}, return: No services configured')
            return 1, None, None

        # Calculate transaction based services
        logger.debug("Calculating transaction based stats")
        df, is_reconciled = self.calc_usage(df, services)  # from ServiceUsageMixin
        return 0, df, is_reconciled
