from django.http import HttpResponse
from pathlib import PurePath

import logging
import zipfile
import io

logger = logging.getLogger(f'et_billing.{__name__}')


def create_zip_file(queryset, zip_file_name) -> HttpResponse:
    """ Create a zipfile containing the files in the provided QuerySet """

    logger.info(f'Creating zip archive {zip_file_name}')
    in_memory_file = io.BytesIO()
    with zipfile.ZipFile(in_memory_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for obj in queryset:

            # Construct the relative path
            file_path = obj.file.path
            parent_dir = PurePath(file_path).parent.name
            filename = PurePath(file_path).name
            rel_path = f"{parent_dir}/{filename}"

            # Add the file with the relative path to the archive
            zip_file.write(file_path, rel_path)

    # Send the zip file as a response for download
    in_memory_file.seek(0)
    response = HttpResponse(in_memory_file.read())
    response['Content-Type'] = 'application/zip'
    response['Content-Disposition'] = f'attachment; filename="{zip_file_name}.zip"'
    return response
