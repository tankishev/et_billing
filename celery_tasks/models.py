from django.db import models


class FileProcessingTask(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=50)
    number_of_files = models.IntegerField(default=0)
    progress = models.IntegerField(default=0)
    processed_documents = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'celery_tasks_file_processing'
