from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from clients.models import Client
from vendors.models import Vendor
from stats.utils import get_stats_usage_not_in_vendor_services as get_su
from vendors.modules.utils import get_vendor_services_not_in_orders as get_vs

from .forms import ReportPeriodForm, ClientPeriodForm, PeriodForm
from .models import ReportFile
from . import modules as m

import os
import logging

logger = logging.getLogger(__name__)


@login_required
def index(request):
    return render(request, 'reports_index.html')


@login_required
def download_billing_report(request, pk):
    try:
        report_file = ReportFile.objects.get(pk=pk)
        filepath = report_file.file.path
        logger.debug(f'Requested file to download: {filepath}')
        return _download_report(filepath)
    except ReportFile.DoesNotExist:
        logger.warning(f'Does Not Exist: ReportFile with id {pk}')
        return HttpResponse('No report file with such id')


@login_required
def download_zoho_report(request, period, filename):
    filepath = str(settings.MEDIA_ROOT / f'output/zoho/{period}/{filename}')
    logger.debug(f'Requested file to download: {filepath}')
    if os.path.exists(filepath):
        return _download_report(filepath)
    logger.warning(f'Does Not Exists: {filepath}')


@login_required
def list_report_files(request):
    context = {
        'page_title': 'Manage Report Files',
        'form_title': 'List billing report files',
        'form_address': '/reports/view-files/',
        'form': PeriodForm()
    }
    if request.method == 'POST':
        form = PeriodForm(request.POST)
        context['form'] = form
        if form.is_valid():
            period = form.cleaned_data.get('period')
            return redirect('list_report_files_period', period)
    return render(request, 'base_form.html', context)


@login_required
def list_report_files_period(request, period):
    files = ReportFile.objects.filter(period=period, type_id=1).order_by('report__client_id')
    if files.exists():
        context = {'files': files, 'period': period}
        return render(request, 'report_file_download.html', context)
    return HttpResponse('No vendor files for this period')


@login_required
def render_period(request):
    context = {
        'page_title': 'Generate Reports',
        'form_title': 'Generate all configured reports',
        'form_subtitle': 'NB! This process can take up to 5 minutes',
        'form_address': '/reports/generate/period-all/',
        'form': PeriodForm()
    }
    return _period_report(request, context, m.gen_reports)


@login_required
def render_period_client(request):
    context = {
        'page_title': 'Generate Reports',
        'form_title': 'Generate all reports for a client',
        'form_address': '/reports/generate/period-client/',
        'form': ClientPeriodForm()
    }
    if request.method == 'POST':
        form = ClientPeriodForm(request.POST)
        if form.is_valid():
            period = form.cleaned_data.get('period')
            client = form.cleaned_data.get('client')
            if client:
                res = m.gen_report_for_client(period, client.client_id)
                context = {
                    'res': res,
                    'period': period
                }
                return render(request, 'report_results.html', context)
    return render(request, 'base_form.html', context)


@login_required
def render_period_report(request):
    context = {
        'page_title': 'Generate Reports',
        'form_title': 'Generate a specific report',
        'form_address': '/reports/generate/period-single/',
        'form': ReportPeriodForm()
    }
    if request.method == 'POST':
        form = ReportPeriodForm(request.POST)
        if form.is_valid():
            period = form.cleaned_data.get('period')
            report = form.cleaned_data.get('report', None)
            if report is not None:
                res = m.gen_report_by_id(period, report.id)
                if res is None:
                    context['err_message'] = f'No data for {report.file_name} in {period}'
                    return render(request, 'base_form.html', context)
                context = {
                    'res': res,
                    'period': period
                }
                return render(request, 'report_results.html', context)
    return render(request, 'base_form.html', context)


@login_required
def reconciliation(request):
    billable_vendors = [el for el in Vendor.objects.filter(
        reports__vendors__reports__isnull=True,
        client__is_billable=True
    )]
    billable_clients_no_report = [el for el in Client.objects.filter(
        is_billable=True,
        reports__isnull=True
    )]
    billable_clients_not_validated = [el for el in Client.objects.filter(
        is_billable=True,
        is_validated=False
    )]
    usage_stats_check = [f'{el.period} Vendor {el.vendor} - Service {el.service}' for el in get_su()]
    vendor_services = [f'Vendor {el[0]} - Service {" ".join(str(x) for x in el[1:])}' for el in get_vs()]
    context = {
        'res_details': {
            (0, 'Vendors not assigned'): [el for el in Vendor.objects.filter(client_id=0)],
            (1, 'Vendors not reconciled'): [el for el in Vendor.objects.filter(is_reconciled=False)],
            (2, 'UsageStats not in VendorServices'): usage_stats_check,
            (3, 'VendorServices not in orders'): vendor_services,
            (4, 'Billable client not-validated'): billable_clients_not_validated,
            (5, 'Billable clients without reports'): billable_clients_no_report,
            (6, 'Billable vendors without report'): billable_vendors
        }
    }
    return render(request, 'results_collapse.html', context)


@login_required
def zoho_service_usage(request):
    context = {
        'page_title': 'Generate Reports',
        'form_title': 'Zoho Reports',
        'form_subtitle': 'Generate services usage report',
        'form_address': '/reports/generate/zoho-service-usage/',
        'form': PeriodForm()
    }
    return _period_report(request, context, m.gen_zoho_usage_summary, zoho=True)


def _download_report(filepath):
    with open(filepath, 'rb') as f:
        response = HttpResponse(f.read(), content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename={}'.format(os.path.basename(filepath))
        return response


def _period_report(request, context, func, zoho=False):
    if request.method == 'POST':
        form = PeriodForm(request.POST)
        if form.is_valid():
            period = form.cleaned_data.get('period')
            res = func(period)
            context = {
                'res': res,
                'period': period,
                'res_zoho': zoho
            }
            return render(request, 'report_results.html', context)
    return render(request, 'base_form.html', context)
