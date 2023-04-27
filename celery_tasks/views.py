# CODE OK
from django.http import JsonResponse
from .models import FileProcessingTask
import logging

logger = logging.getLogger('et_billing.celery_tasks.view')


def get_task_progress(request, task_id: str) -> JsonResponse:
    """ Gets the status of a Celery task provided its task_id """
    try:
        task_status = FileProcessingTask.objects.get(task_id=task_id)
        return JsonResponse({
            'taskStatus': task_status.status,
            'taskProgress': task_status.progress,
            'fileList': task_status.processed_documents,
            'progressStatus': f'Processed files {len(task_status.processed_documents)}/{task_status.number_of_files}'
        })
    except FileProcessingTask.DoesNotExist:
        logger.warning(f'DoesNotExists: task {task_id}')
        return JsonResponse({'progress': 0})
