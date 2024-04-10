from celery import shared_task
from celery_tasks.models import FileProcessingTask
from celery.utils.log import get_task_logger

from .base_rater import BaseRater
from clients.models import Client

import time
import logging

logger = logging.getLogger(f'et_billing.{__name__}')
celery_logger = get_task_logger(f'et_billing.{__name__}')


@shared_task(bind=True)
def rate_transactions(self, period):

    start_time = time.time()
    logger.info(f"Starting rating of transactions for ALL vendors for {period}.")

    # Create file processing task
    task_status = FileProcessingTask.objects.create(task_id=self.request.id, status='PROGRESS', progress=0)
    task_status.save()

    br = BaseRater(period)
    clients = list(Client.objects.filter(is_billable=True).order_by('client_id'))
    number_of_clients = len(clients)

    for i, client in enumerate(clients):
        br.rate_client_transactions(client.pk)

        task_status.progress = min(100 * i // number_of_clients, 100)
        task_status.save()

    # Updated at complete
    task_status.progress = 100
    task_status.status = 'COMPLETE'
    task_status.save()

    end_time = time.time()
    execution_minutes = end_time - start_time
    minutes = int(execution_minutes // 60)
    seconds = int(execution_minutes % 60)

    logger.info(f'Data import process completed in {minutes} minutes and {seconds} seconds')
