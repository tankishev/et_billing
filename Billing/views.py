from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(f'et_billing.{__name__}')


@login_required
def index(request):
    return render(request, 'index.html')


@csrf_exempt
def log_json(request):
    if request.method == 'POST':
        json_data = request.body.decode('utf-8')
        logger.info(f'Received JSON data: {json_data}')
        return JsonResponse({}, status=200)
    else:
        return JsonResponse({}, status=405)
