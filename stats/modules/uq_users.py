# CODE TO BE TESTED
from datetime import datetime as dt
from celery import shared_task
from celery_tasks.models import FileProcessingTask
from clients.models import Client
from vendors.modules.input_files import InputFilesMixin
from vendors.models import VendorInputFile, Vendor
from ..models import UniqueUser, UquStatsPeriodClient, UquStatsPeriodVendor, UquStatsPeriod

import logging

logger = logging.getLogger('et_billing.stats.uq_users')


def get_uqu(client_id=None, start_period=None, end_period=None) -> int:
    """ Returns a QuerySet object with data based on input options """

    # QuerySets for specific client_id
    if client_id is None:
        if start_period is None and end_period is None:
            uqu_data = UniqueUser.objects.all().values_list('user_id', flat=True).distinct()
        elif end_period is None:
            uqu_data = UniqueUser.objects.filter(month__range=[start_period, start_period]) \
                .values_list('user_id', flat=True).distinct()
        else:
            uqu_data = UniqueUser.objects.filter(month__range=[start_period, end_period]) \
                .values_list('user_id', flat=True).distinct()

    # QuerySets for the whole company
    else:
        if start_period is None and end_period is None:
            uqu_data = UniqueUser.objects.filter(vendor__client__client_id=client_id) \
                .values_list('user_id', flat=True).distinct()
        elif end_period is None:
            uqu_data = UniqueUser.objects \
                .filter(vendor__client__client_id=client_id, month__range=[start_period, start_period]) \
                .values_list('user_id', flat=True).distinct()
        else:
            uqu_data = UniqueUser.objects \
                .filter(vendor__client__client_id=client_id, month__range=[start_period, end_period]) \
                .values_list('user_id', flat=True).distinct()

    return len(uqu_data)


@shared_task(bind=True)
def store_uqu_celery(self):
    """ Run all Unique Users calculations """

    start = dt.now()
    logger.info(f"Starting unique usage calculations")

    # Create file processing task
    task_status = FileProcessingTask.objects.create(task_id=self.request.id, status='PROGRESS', progress=0)
    task_status.processed_documents.append({
        'fileName': 'Saving data for unique users',
        'resultCode': 3,
        'resultText': 'starting',
    })
    task_status.save()

    try:
        store_unique_users()
        task_status.processed_documents.extend([{
            'fileName': 'Saving data for unique users ',
            'resultCode': 0,
            'resultText': 'done',
        }, {
            'fileName': 'Calculating unique users by period',
            'resultCode': 3,
            'resultText': 'starting',
        }])
        task_status.progress = 25
        task_status.save()

        store_uqu_periods()
        task_status.processed_documents.extend([{
            'fileName': 'Calculating unique users by period ',
            'resultCode': 0,
            'resultText': 'done',
        }, {
            'fileName': 'Calculating unique users by vendor and period',
            'resultCode': 3,
            'resultText': 'starting',
        }])
        task_status.progress = 50
        task_status.save()

        store_uqu_vendors()
        task_status.processed_documents.extend([{
            'fileName': 'Calculating unique users by vendor and period ',
            'resultCode': 0,
            'resultText': 'done',
        }, {
            'fileName': 'Calculating unique users by client and period',
            'resultCode': 3,
            'resultText': 'starting',
        }])
        task_status.progress = 75
        task_status.save()

        store_uqu_clients()
        task_status.processed_documents.append({
            'fileName': 'Calculating unique users by client and period ',
            'resultCode': 0,
            'resultText': 'done',
        })
        task_status.progress = 100
        task_status.status = 'COMPLETE'
        task_status.save()

    except Exception as err:
        logger.warning(err)
        task_status.status = 'FAILED'
        task_status.save()

    finally:
        execution_time = dt.now() - start
        logger.info(f'Execution time: {execution_time}')


def store_unique_users(purge_existing=False):
    """ Store unique users at company level for all periods """

    logger.info('Starting storing of unique users')
    mx = InputFilesMixin()
    retval = []
    dt_start = dt.now()

    # Clear all existing information
    if purge_existing:
        UniqueUser.objects.all().delete()

    # Get a query set with VendorInputFiles and list of already processed (period, vendor_id)
    vendor_input_files = VendorInputFile.objects.all().order_by('period', 'vendor_id')
    uqu_data = list(UniqueUser.objects.values_list('month', 'vendor_id').distinct())

    for input_file in vendor_input_files:
        vendor_id, period = input_file.vendor_id, input_file.period

        # If period and vendor are already processed then move to next file
        if (period, vendor_id) in uqu_data:
            continue

        # Load unique users data
        logger.debug(f'Getting unique users for vendor {vendor_id} for {period}')
        unique_pids = mx.load_data_for_uq_countries(input_file.file.path)
        unique_pids = [(el[0], el[1]) for el in unique_pids if el[1] != '']

        # Save unique users data
        if len(unique_pids) == 0:
            logger.debug('No unique users data')
            continue

        logger.debug(f'Found {len(unique_pids)} unique users')
        unique_users = [
            UniqueUser(
                month=period,
                vendor_id=vendor_id,
                user_id=f'{country}{pid}',
                country=country)
            for country, pid in unique_pids]
        UniqueUser.objects.bulk_create(unique_users)
        logger.debug('Data saved')

        retval.append(f'{input_file.file.path} - processed')

    processing_time = dt.now() - dt_start
    logger.info(f'Execution time: {processing_time}')


def store_uqu_clients(purge_existing=False):
    """ Store unique users data per client per period """

    dt_start = dt.now()
    logger.info('Starting calculation of unique users per client per period')

    # Clear all existing information
    if purge_existing:
        UquStatsPeriodClient.objects.all().delete()

    # Get clients for which computation should be made
    clients = Client.objects.filter(vendors__unique_users__isnull=False).distinct()

    # Cycle through clients and compute
    for client in clients:
        logger.debug(f'Processing client: {client.client_id}')

        # Get the vendors related to this client
        vendors = list(Vendor.objects.filter(client=client).values_list('vendor_id', flat=True))

        # Get the months for which there is already unique users data
        uqu_data = list(UquStatsPeriodClient.objects
                        .filter(client=client)
                        .order_by('-period')
                        .values_list('period', flat=True).distinct())

        # Get the months for which data needs to be added
        months = list(UniqueUser.objects
                      .filter(vendor_id__in=vendors)
                      .order_by('month')
                      .values_list('month', flat=True).distinct())
        months_to_process = [el for el in months if el not in uqu_data]

        # Cycle through months and compute cumulative unique users
        first_month = months[0]
        prior_month = uqu_data[0] if uqu_data else first_month
        for month in months_to_process:
            # Try to skip calculations if there is 1 vendor per client and is already processed
            if len(vendors) == 1 and UquStatsPeriodVendor.objects.filter(vendor_id=vendors[0], period=month).exists():
                data = UquStatsPeriodVendor.objects.get(vendor_id=vendors[0], period=month)
                cumulative, period_count, new_count = data.cumulative, data.uqu_month, data.uqu_new

            else:
                # Get cumulative unique users for the period from the start till current month
                cumulative = len(UniqueUser.objects
                                 .filter(vendor_id__in=vendors, month__range=[first_month, month])
                                 .values_list('user_id', flat=True).distinct())

                # Get the total unique users for the current month
                period_count = len(UniqueUser.objects
                                   .filter(vendor_id__in=vendors, month=month)
                                   .values_list('user_id', flat=True).distinct())

                # Calculate the number of unique users appeared for the first time in the current period
                prior_count = 0
                if month != first_month:
                    prior_record = UquStatsPeriodClient.objects.get(period=prior_month, client=client)
                    prior_count = prior_record.cumulative
                new_count = cumulative - prior_count

            # Save statistics
            UquStatsPeriodClient.objects.create(
                period=month,
                client=client,
                cumulative=cumulative,
                uqu_month=period_count,
                uqu_new=new_count
            ).save()
            prior_month = month
            logger.debug(f'... {month} complete')

        logger.info(f'Client {client.client_id} complete')

    execution_time = dt.now() - dt_start
    logger.info(f'Execution time: {execution_time}')


def store_uqu_periods(purge_existing=False):
    """ Store unique users data per period at company level """

    dt_start = dt.now()
    logger.info('Starting calculation of unique users per period')

    # Clear all existing information
    if purge_existing:
        UquStatsPeriod.objects.all().delete()

    # Get the months for which there is already unique users data
    uqu_data = list(UquStatsPeriod.objects
                    .order_by('-period')
                    .values_list('period', flat=True).distinct())

    # Get the months for which data needs to be added
    months = list(UniqueUser.objects.all()
                  .order_by('month')
                  .values_list('month', flat=True).distinct())
    months_to_process = [el for el in months if el not in uqu_data]

    # Cycle through months and compute cumulative unique users
    first_month = months[0]
    prior_month = uqu_data[0] if uqu_data else first_month
    for month in months_to_process:
        logger.info(f'Processing month: {month}')

        # Get cumulative unique users for the period from the start till current month
        cumulative = len(UniqueUser.objects.filter(month__range=[first_month, month])
                         .values_list('user_id', flat=True).distinct())

        # Get the total unique users for the current month
        period_count = len(UniqueUser.objects.filter(month=month)
                           .values_list('user_id', flat=True).distinct())

        # Calculate the number of unique users appeared for the first time in the current period
        prior_count = 0
        if month != first_month:
            prior_record = UquStatsPeriod.objects.get(period=prior_month)
            prior_count = prior_record.cumulative
        new_count = cumulative - prior_count

        # Save statistics
        UquStatsPeriod.objects.create(
            period=month,
            cumulative=cumulative,
            uqu_month=period_count,
            uqu_new=new_count
        ).save()
        prior_month = month
        logger.info(f'{month} complete')

    execution_time = dt.now() - dt_start
    logger.info(f'Execution time: {execution_time}')


def store_uqu_vendors(purge_existing=False):
    """ Store unique users data per vendor per period """

    dt_start = dt.now()
    logger.info('Starting calculation of unique users per vendor per period')

    # Clear all existing information
    if purge_existing:
        UquStatsPeriodVendor.objects.all().delete()

    # Get vendors for which computation should be made
    vendors = UniqueUser.objects.values_list('vendor_id', flat=True).distinct()

    # Cycle through vendors and compute
    for vendor_id in vendors:
        logger.debug(f'Processing vendor: {vendor_id}')

        # Get the months for which there is already unique users data
        uqu_data = list(UquStatsPeriodVendor.objects
                        .filter(vendor_id=vendor_id)
                        .order_by('-period')
                        .values_list('period', flat=True).distinct())

        # Get the months for which data needs to be added
        months = list(UniqueUser.objects
                      .filter(vendor_id=vendor_id)
                      .order_by('month')
                      .values_list('month', flat=True).distinct())
        months_to_process = [el for el in months if el not in uqu_data]

        # Cycle through months and compute unique users
        first_month = months[0]
        prior_month = uqu_data[0] if uqu_data else first_month
        for month in months_to_process:

            # Get cumulative unique users for the period from the start till current month
            cumulative = len(UniqueUser.objects
                             .filter(vendor_id=vendor_id, month__range=[first_month, month])
                             .values_list('user_id', flat=True).distinct())

            # Get the total unique users for the current month
            period_count = len(UniqueUser.objects
                               .filter(vendor_id=vendor_id, month=month)
                               .values_list('user_id', flat=True).distinct())

            # Calculate the number of unique users appeared for the first time in the current period
            prior_count = 0
            if month != first_month:
                prior_record = UquStatsPeriodVendor.objects.get(period=prior_month, vendor_id=vendor_id)
                prior_count = prior_record.cumulative
            new_count = cumulative - prior_count

            # Save statistics
            UquStatsPeriodVendor.objects.create(
                period=month,
                vendor_id=vendor_id,
                cumulative=cumulative,
                uqu_month=period_count,
                uqu_new=new_count
            ).save()
            prior_month = month
            logger.debug(f'... {month} complete')

        logger.info(f'Vendor {vendor_id} complete')

    execution_time = dt.now() - dt_start
    logger.info(f'Execution time: {execution_time}')
