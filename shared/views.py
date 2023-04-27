# CODE OK
from django.http import HttpResponse
import os


def download_excel_file(filepath) -> HttpResponse:
    """ Method for downloading Excel files """

    with open(filepath, 'rb') as f:
        response = HttpResponse(f.read(), content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename={}'.format(os.path.basename(filepath))
        return response
