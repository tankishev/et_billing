from datetime import datetime as dt
from vendors.models import VendorInputFile
from .db_update import DBUpdater


def recalc_vendor(period, vendor_id):
    start = dt.now()
    try:
        input_file = VendorInputFile.objects.get(period=period, vendor_id=vendor_id, is_active=True)
        dbu = DBUpdater()
        res = dbu.save_service_usage_period_vendor(input_file)
        return res, vendor_id
    except VendorInputFile.DoesNotExist:
        return 2, vendor_id
    finally:
        print(dt.now() - start)


def recalc_all_vendors(period):
    start = dt.now()
    output = dict()
    try:
        input_files = VendorInputFile.objects.filter(period=period, is_active=True).order_by('vendor_id')
        dbu = DBUpdater()
        for input_file in input_files:
            res = dbu.save_service_usage_period_vendor(input_file)
            if res not in output:
                output[res] = []
            output[res].append(input_file.vendor_id)
        return output
    except VendorInputFile.DoesNotExist:
        return output
    finally:
        print(dt.now() - start)
