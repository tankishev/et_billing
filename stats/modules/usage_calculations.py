from celery import shared_task
from celery_tasks.models import FileProcessingTask
from celery.utils.log import get_task_logger

from vendors.models import VendorInputFile
from .calculator import ServiceUsageCalculator, UnreconciledTransactionsMapper, res_result
from ..models import Service

from datetime import datetime as dt
from pathlib import PurePath
import logging

logger = logging.getLogger(f'et_billing.{__name__}')
celery_logger = get_task_logger(f'et_billing.{__name__}')


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
        celery_logger.debug("Service usage calculated. Saving results.")

        # Update the task to add the filename
        input_file_path = PurePath(input_file.file.path)
        dir_name = input_file_path.parts[-2]
        task_status.processed_documents.append({
            'fileId': input_file.id,
            'fileName': dir_name,
            'resultCode': res,
            'resultText': res_result(res)
        })

        task_status.progress = 100
        task_status.status = 'COMPLETE'
        task_status.save()
        celery_logger.debug("Completed service usage calculations")

    except VendorInputFile.DoesNotExist:
        message = f"No usage file for vendor {vendor_id} in {period}."
        celery_logger.warning(message)
        task_status.note = message
        task_status.status = 'FAILED'
        task_status.save()
        return 2, vendor_id

    except Exception as e:
        message = f"An unexpected error occurred: {e}"
        celery_logger.error(message)
        task_status.note = message
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
            VendorInputFile.objects.filter(
                period__lt=period,
                is_active=True
            ).values_list('vendor_id', flat=True).distinct()
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
        message = "No input files found"
        celery_logger.warning(message)
        task_status.note = message
        task_status.status = 'FAILED'
        task_status.save()

    finally:
        execution_time = dt.now() - start
        celery_logger.info(f'Execution time: {execution_time}')


def get_vendor_unreconciled(file_id: int) -> dict:
    """ Returns a dict with unreconciled transactions and suggested service for them.
        Used for population of Unreconciled transactions modal.
    """

    logger.info(f"Mapping transactions for VendorInputFile pk {file_id}")
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
        logger.warning(f"No VendorInputFile with id {file_id}")

    finally:
        execution_time = dt.now() - start
        logger.info(f"Execution time: {execution_time}")
