from django.db import connection
from django.conf import settings
from vendors.models import VendorInputFile
from .calculator import BaseServicesMapper
from ..models import UsageTransaction, TransactionStatus

from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import csv
import os
import time


logger = logging.getLogger(f'et_billing.{__name__}')


def load_transactions_csv(period, vendor_ids=None):
    logger.info(f'Starting loading transactions for {period}')
    start_time = time.time()

    vendor_files = VendorInputFile.objects.filter(period=period)
    if vendor_ids:
        logger.info(f'... filtering only vendors {vendor_ids}')
        vendor_files = vendor_files.filter(vendor_id__in=vendor_ids)

    if not vendor_files.exists():
        logger.warning(f'No input files for {period}')
        return
    vendor_files = list(vendor_files)

    # Remove existing transactions for the same period and vendors
    logger.debug('Deleting existing transactions')
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
    existing_data.delete()

    # Calculate and save new transactions
    logger.debug(f'VendorInputFiles selected: {len(vendor_files)}')
    mapper = BaseServicesMapper()
    transaction_status_cache = list(TransactionStatus.objects.all().values_list('status_type', flat=True))

    for input_file in vendor_files:
        vendor_id = input_file.vendor_id
        csv_filename = os.path.join(settings.MEDIA_ROOT, f'transactions_{period}_{vendor_id}.csv')

        try:
            logger.debug(f'Mapping transactions for vendor {vendor_id}')
            status, mapped_transactions = mapper.map_service_usage(input_file, skip_status_five=False)

            if mapped_transactions is None:
                continue

            logger.debug(f'Writing {len(mapped_transactions.transactions)} transactions to temp CSV file')
            with open(csv_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                for item in mapped_transactions.transactions:
                    if item.transaction_status not in transaction_status_cache:
                        logger.warning(f'Transaction status {item.transaction_status} is not defined')
                        continue

                    writer.writerow([
                        item.date_created,
                        input_file.vendor_id,
                        item.thread_id,
                        item.transaction_id,
                        item.transaction_status,
                        item.service_id if item.service_id is not None else '',
                        item.payer == 'Client',
                        item.bio == 'yes'
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

        except Exception as e:
            logger.error(f'An error occurred during transactions import: {e}')

        finally:
            # Remove the CSV file whether the import was successful
            if os.path.exists(csv_filename):
                os.remove(csv_filename)
                logger.debug('Temporary CSV file removed')

    end_time = time.time()
    execution_minutes = end_time - start_time
    minutes = int(execution_minutes // 60)
    seconds = int(execution_minutes % 60)

    logger.info(f'Data import process completed in {minutes} minutes and {seconds} seconds')
