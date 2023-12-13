from celery import shared_task
from celery_tasks.models import FileProcessingTask
from celery.utils.log import get_task_logger

from vendors.models import VendorInputFile
from .calculator import ServiceUsageCalculator

from datetime import datetime as dt
from pathlib import PurePath
import logging

logger = logging.getLogger('et_billing.stats_vendors_calc')
celery_logger = get_task_logger('stats.vendors_calc')


def res_result(res_id):
    """ Return verbose names for the results of the calc_vendor functions """

    update_vendor_legend = {
        0: 'Complete',
        1: 'No services configured',
        2: 'No input file',
        3: 'No transactions',
        4: 'Not reconciled'
    }
    return update_vendor_legend.get(res_id, 'Not defined')


@shared_task(bind=True)
def recalc_vendor(self, period, vendor_id):
    """ Calculate vendor usage for a given period and vendor_id"""
    start = dt.now()
    celery_logger.info(f"Starting usage calcs for vendor {vendor_id} for {period}.")

    # Create file processing task
    task_status = FileProcessingTask.objects.create(
        task_id=self.request.id, status='PROGRESS', progress=0, number_of_files=1)
    task_status.save()

    try:
        # Load input file
        input_file = VendorInputFile.objects.get(period=period, vendor_id=vendor_id, is_active=True)
        celery_logger.debug("Input file loaded")

        # Process file
        calc = ServiceUsageCalculator()
        res = calc.save_service_usage_period_vendor(input_file)

        # Update the task to add the filename
        input_file_path = PurePath(input_file.file.path)
        dir_name = input_file_path.parts[-2]
        task_status.processed_documents.append({
            'fileName': dir_name,
            'resultCode': res,
            'resultText': res_result(res)
        })

        task_status.progress = 100
        task_status.status = 'COMPLETE'
        task_status.save()

    except VendorInputFile.DoesNotExist:
        celery_logger.warning(f"No usage file for vendor {vendor_id} in {period}.")
        task_status.status = 'FAILED'
        task_status.save()
        return 2, vendor_id

    except Exception as e:
        celery_logger.error(f"An unexpected error occurred: {e}")
        task_status.status = 'FAILED'
        task_status.save()
        raise

    finally:
        execution_time = dt.now() - start
        celery_logger.info(f'Execution time: {execution_time}')


@shared_task(bind=True)
def recalc_all_vendors(self, period):
    """ Calculate vendor usage for all vendors for a given period """

    start = dt.now()
    logger.info(f"Starting usage calcs for ALL vendors for {period}.")

    # Create file processing task
    task_status = FileProcessingTask.objects.create(task_id=self.request.id, status='PROGRESS', progress=0)
    task_status.save()

    try:
        # Load input files
        input_files = VendorInputFile.objects.filter(period=period, is_active=True).order_by('vendor_id')
        number_of_files = len(input_files)
        task_status.number_of_files = number_of_files
        task_status.save()
        logger.debug(f'{number_of_files} input files loaded')
        prior_vendors_list = list(
            VendorInputFile.objects.filter(period__lt=period).values_list('vendor_id', flat=True).distinct()
        )

        # Process files
        calc = ServiceUsageCalculator()
        for i, input_file in enumerate(input_files):

            # Calculate usage
            res = calc.save_service_usage_period_vendor(input_file)

            # Update the task to add the filename
            input_file_path = PurePath(input_file.file.path)
            dir_name = input_file_path.parts[-2]
            if input_file.vendor_id not in prior_vendors_list:
                dir_name = f'*NEW* {dir_name}'
            task_status.processed_documents.append({
                'fileName': dir_name,
                'resultCode': res,
                'resultText': res_result(res),
                'fileId': input_file.id
            })
            task_status.progress = min(100 * i // number_of_files, 100)
            task_status.save()

        # Updated at complete
        task_status.progress = 100
        task_status.status = 'COMPLETE'
        task_status.save()

    except VendorInputFile.DoesNotExist:
        celery_logger.warning("No input files found")
        task_status.status = 'FAILED'
        task_status.save()

    finally:
        execution_time = dt.now() - start
        celery_logger.info(f'Execution time: {execution_time}')
