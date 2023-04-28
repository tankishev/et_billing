from django.db import models
import json


class ProcessedDocumentsList(models.JSONField):
    def __init__(self, *args, **kwargs):
        kwargs['blank'] = True
        kwargs['null'] = True
        kwargs['default'] = list
        super().__init__(*args, **kwargs)

    # Read from DB
    def to_python(self, value):
        if value is None:
            return []
        if isinstance(value, str):
            value = json.loads(value)
        return [
            {
                'fileName': item.get('fileName', ''),
                'fileId': int(item['fileId']) if 'fileId' != '' else None,
                'resultCode': int(item['resultCode']) if 'resultCode' != '' else None,
                'resultText': item.get('resultText', '')
            }
            for item in value
        ]

    # Save to DB
    def get_prep_value(self, value):
        if value is None:
            return json.dumps([])
        return json.dumps([
            {
                'fileName': item.get('fileName', ''),
                'fileId': item.get('fileId', ''),
                'resultCode': item.get('resultCode', ''),
                'resultText': item.get('resultText', '')
            }
            for item in value
        ])


class FileProcessingTask(models.Model):
    """ Model to store file processing Celery tasks """

    task_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=50)
    number_of_files = models.IntegerField(default=0)
    progress = models.IntegerField(default=0)
    processed_documents = ProcessedDocumentsList()

    class Meta:
        db_table = 'celery_tasks_file_processing'
