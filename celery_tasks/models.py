from django.db import models
import json


class ProcessedDocumentsList(models.JSONField):
    """ Customised JSONField """

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
                'fileId': int(item['fileId']) if item.get('fileID') not in (None, '') else None,
                'resultCode': int(item['resultCode']) if item.get('resultCode') not in (None, '') else None,
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
    note = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'celery_tasks_file_processing'
