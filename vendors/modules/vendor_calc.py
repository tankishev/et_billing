from datetime import datetime as dt
from vendors.models import VendorInputFile
from .db_update import DBUpdater
import logging

logger = logging.getLogger(__name__)


def recalc_vendor(period, vendor_id):
    logger.info(f"Starting usage calcs for vendor {vendor_id} for {period}.")
    start = dt.now()
    try:
        input_file = VendorInputFile.objects.get(period=period, vendor_id=vendor_id, is_active=True)
        logger.debug("Input file loaded")
        dbu = DBUpdater()
        res = dbu.save_service_usage_period_vendor(input_file)
        logger.debug(f"Calc result: {res}")
        return res, vendor_id
    except VendorInputFile.DoesNotExist:
        logger.warning(f"No usage file for vendor {vendor_id} in {period}.")
        return 2, vendor_id
    finally:
        execution_time = dt.now - start
        logger.info(f'Execution time: {execution_time}')


def recalc_all_vendors(period):
    logger.info(f"Starting usage calcs for ALL vendors for {period}.")
    start = dt.now()
    output = dict()
    try:
        input_files = VendorInputFile.objects.filter(period=period, is_active=True).order_by('vendor_id')
        logger.debug(f'{len(input_files)} input files loaded')
        dbu = DBUpdater()
        for input_file in input_files:
            res = dbu.save_service_usage_period_vendor(input_file)
            if res not in output:
                output[res] = []
            output[res].append(input_file.vendor_id)
        return output
    except VendorInputFile.DoesNotExist:
        logger.warning("No input files found")
        return output
    finally:
        execution_time = dt.now() - start
        logger.info(f'Execution time: {execution_time}')
