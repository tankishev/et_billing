from django.http import JsonResponse
from .models import FileProcessingTask
import logging

logger = logging.getLogger('celery_tasks.view')


def get_task_progress(request, task_id: str):
    try:
        logger.debug(f'Looking for task {task_id}')
        task_status = FileProcessingTask.objects.get(task_id=task_id)
        return JsonResponse({
            'status': task_status.status,
            'progress': task_status.progress,
            'processed_documents_list': task_status.processed_documents,
            'progress_status': f'Processed files {len(task_status.processed_documents)}/{task_status.number_of_files}'
        })
    except FileProcessingTask.DoesNotExist:
        logger.warning(f'DoesNotExists: task {task_id}')
        return JsonResponse({'progress': 0})

