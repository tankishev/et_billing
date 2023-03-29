from services.modules import FiltersMixin
from shared.modules import DBProxy
from stats.modules import save_service_usage

from .input_files import InputFilesMixin
from .service_usage import ServiceUsageMixin
from ..models import Vendor, VendorService


class DBUpdater(FiltersMixin, ServiceUsageMixin, InputFilesMixin):

    def __init__(self):
        self.dba = DBProxy()

    def save_service_usage_period_vendor(self, input_file, skip_status_five=True):
        """ Read vendor input file and calculate service usage """

        period, vendor_id = input_file.period, input_file.vendor_id

        # Load dataframe and convert all numbers
        df = self.load_data_for_service_usage(input_file.file.path, skip_status_five)
        if df is None:
            print(f'{period}: {vendor_id} - No transactions')
            return 3

        # Load service filters
        service_filters = self.get_service_filters()
        services = self.load_vendor_service_filters(vendor_id, service_filters)
        if services is None:
            print(f'{period}: {vendor_id} - No services configured')
            return 1

        # Calculate transaction based services
        df, is_reconciled = self.calc_usage(df, services)
        self.update_vendor_is_reconciled(vendor_id, is_reconciled)
        if not is_reconciled:
            print(f'{period}: {vendor_id} - Not reconciled')
            return 4

        # Get transaction based stats
        res = df.service_id.value_counts()
        data = [(k, v) for k, v in res.items() if v is not None]

        # Get aggregation based stats
        if data and "Bio required" in df.columns:
            df_bio = df[df["Bio required"] == 'yes'][["ThreadID"]].copy()
            df_bio = df_bio.drop_duplicates()
            n = len(df_bio)
            if n > 0:
                data.append((50, n))

        # Add unique users where enabled requiring enablement
        if VendorService.objects.filter(vendor_id=vendor_id, service_id=32).exists():
            n = df["PID receiver"].dropna().nunique()
            if n > 0:
                data.append((32, n))

        # Save usage stats
        for el in data:
            save_service_usage((period, vendor_id, *el))
        print(f'{period}: {vendor_id} - Complete')
        return 0

    @staticmethod
    def update_vendor_is_reconciled(vendor_id, is_reconciled=False):
        vendor = Vendor.objects.get(vendor_id=vendor_id)
        if vendor.is_reconciled != is_reconciled:
            vendor.is_reconciled = is_reconciled
            vendor.save()
