from django.http import HttpResponse

from rest_framework.request import Request
from .modules.base_rater import BaseRater
from clients.models import Client


def debug_view(request: Request):
    period = '2023-11'
    client_id = request.GET.get('client_id', 21)
    clients = Client.objects.filter(is_billable=True).order_by('client_id')
    br = BaseRater(period)
    for client in clients:
        br.rate_client_transactions(client.pk)
    return HttpResponse('OK')
