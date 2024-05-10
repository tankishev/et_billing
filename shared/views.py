from django.http import FileResponse
from urllib.parse import quote
import os


def download_excel_file(filepath) -> FileResponse:
    """ Method for downloading Excel files """

    file_basename = os.path.basename(filepath)
    quoted_filename = quote(file_basename)

    response = FileResponse(
        open(filepath, 'rb'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    response['Content-Disposition'] = f'attachment; filename="{quoted_filename}"'
    return response
