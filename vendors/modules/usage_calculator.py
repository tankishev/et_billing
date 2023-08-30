# CODE OK
from shared.modules import BaseServiceUsageCalculator
from stats.modules import save_service_usage
from ..models import Vendor, VendorService

import logging

logger = logging.getLogger('et_billing.vendors.usage_calculator')


class ServiceUsageCalculator(BaseServiceUsageCalculator):
    """ A helper class that calculates and save vendor service usage """
    _BIO_AUTH_SERVICE_ID = 50
    _LEGAL_PERSONS_SERVICE_ID = 36
    _UNIQUE_USERS_SERVICE_ID = 32

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
