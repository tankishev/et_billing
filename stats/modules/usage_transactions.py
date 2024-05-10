from celery import shared_task
from celery_tasks.models import FileProcessingTask
from celery.utils.log import get_task_logger

from django.db import connection
from django.conf import settings
from vendors.models import VendorInputFile
from .calculator import BaseServicesMapper, res_result
from ..models import UsageTransaction, TransactionStatus

from pathlib import PurePath
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import csv
import os
import time


logger = logging.getLogger(f'et_billing.{__name__}')
# logger = logging.getLogger(f'simple_test_logger') CONTINUE HERE
celery_logger = get_task_logger(f'et_billing.{__name__}')


# def test_logging():
#     logger.debug(f"Name is {__name__}")
#     et_logger.debug(f"Name is {__name__}")
#     celery_logger.debug(f"Name is {__name__}")


@shared_task(bind=True)
def load_transactions(self, period, vendor_ids=None):
    # print("Task started - this should appear in the Celery worker's console")
    # test_logging()
    # logger.debug("Testing et_billing logger at the start of the task")
    # et_logger.debug("Testing et_billing logger at the start of the task")
    # celery_logger.debug("Testing Celery logger at the start of the task")


    """ Reads Iteco raw files for a given period and list of accounts and loads stats_usage_transactions for them.
        Removes exiting transactions for the given period and accounts if such exist before saving the new ones.
        When calculating usage it stores the data in a temp CSV file in order to improve performance on DB import.
    """

    celery_logger.info(f'Starting loading transactions for {period}')
    start_time = time.time()

    # Create file processing Celery task
    task_status = FileProcessingTask.objects.create(task_id=self.request.id, status='PROGRESS', progress=0)
    task_status.save()

    # Set raw input files queryset
    vendor_files = VendorInputFile.objects.filter(period=period, is_active=True)
    if vendor_ids:
        logger.info(f'... filtering only vendors {vendor_ids}')
        vendor_files = vendor_files.filter(vendor_id__in=vendor_ids)

    # Exit of input files queryset is empty
    if not vendor_files.exists():
        logger.warning(f'No input files for {period}')
        return
    vendor_files = list(vendor_files)

    # Remove existing transactions for the same period and vendors
    period_start = datetime.strptime(period, '%Y-%m')
    period_end = period_start + relativedelta(months=1)
    existing_data = UsageTransaction.objects.filter(
        timestamp__gte=period_start,
        timestamp__lt=period_end
    )
    if vendor_ids:
        existing_data = existing_data.filter(
            vendor_id__in=vendor_ids
        )
    if existing_data.exists():
        logger.debug('Deleting existing transactions')
        existing_data.delete()

    # Process each individual file and save new transactions
    number_of_files = len(vendor_files)
    logger.debug(f'Number of selected VendorInputFiles: {number_of_files}')
    mapper = BaseServicesMapper()
    transaction_status_cache = list(TransactionStatus.objects.all().values_list('status_type', flat=True))

    for i, input_file in enumerate(vendor_files):
        vendor_id = input_file.vendor_id
        csv_filename = os.path.join(settings.MEDIA_ROOT, f'transactions_{period}_{vendor_id}.csv')

        try:
            # Map transactions
            logger.debug(f'Mapping transactions for vendor {vendor_id}')
            status, mapped_transactions = mapper.map_service_usage(input_file, skip_status_five=False)
            # print(status, len(mapped_transactions))

            if mapped_transactions is None:
                continue

            # Store data in temp CSV file (for faster import to DB)
            logger.debug(f'Writing {len(mapped_transactions.transactions)} transactions to temp CSV file')
            first_transaction = mapped_transactions.transactions[0]
            has_thread_id = hasattr(first_transaction, 'thread_id')
            has_bio = hasattr(first_transaction, 'bio')

            with open(csv_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                for item in mapped_transactions.transactions:
                    if item.transaction_status not in transaction_status_cache:
                        logger.warning(f'Transaction status {item.transaction_status} is not defined')
                        continue

                    thread_id = item.thread_id if has_thread_id else ''
                    payer_boolean = item.payer == 'Client'
                    bio_boolean = item.bio == 'yes' if has_bio else False

                    writer.writerow([
                        item.date_created,
                        input_file.vendor_id,
                        thread_id,
                        item.transaction_id,
                        item.transaction_status,
                        item.service_id if item.service_id is not None else '',
                        payer_boolean,
                        bio_boolean
                    ])

            # Import new transactions from CSV
            logger.debug('Importing new transactions')
            with connection.cursor() as cursor, open(csv_filename, 'r') as csv_file:
                cursor.copy_from(
                    csv_file, 'stats_usage_transactions', sep=',', null='',
                    columns=(
                        'timestamp',
                        'vendor_id',
                        'thread_id',
                        'transaction_id',
                        'status_id',
                        'service_id',
                        'charge_user',
                        'bio_pin'
                    ))

            # Update the task to add the filename
            input_file_path = PurePath(input_file.file.path)
            dir_name = input_file_path.parts[-2]
            task_status.processed_documents.append({
                'fileId': input_file.id,
                'fileName': dir_name,
                'resultCode': status,
                'resultText': res_result(status)
            })
            task_status.progress = min(100 * i // number_of_files, 100)
            task_status.save()

        except Exception as e:
            logger.error(f'An error occurred during transactions import: {e}')

        finally:
            # Remove the CSV file whether the import was successful
            if os.path.exists(csv_filename):
                os.remove(csv_filename)
                logger.debug('Temporary CSV file removed')

    # Updated at complete
    task_status.progress = 100
    task_status.status = 'COMPLETE'
    task_status.save()

    end_time = time.time()
    execution_minutes = end_time - start_time
    minutes = int(execution_minutes // 60)
    seconds = int(execution_minutes % 60)

    celery_logger.info(f'Data import process completed in {minutes} minutes and {seconds} seconds')
