from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from shared.modules import create_zip_file
from shared.views import download_excel_file
from stats.utils import get_stats_usage_not_in_vendor_services as get_su
from vendors.models import VendorService

from .forms import ReportPeriodForm, ClientPeriodForm, PeriodForm
from .models import ReportFile, Client, Vendor
from . import modules as m

import os
import logging

logger = logging.getLogger(f'et_billing.{__name__}')


def index(request):
    """ Returns index page for the reports module """
    return render(request, 'reports/reports_index.html')


# BILLING REPORTS CALCULATIONS
def render_period(request):
    """ Triggers the rendering of reports for ALL clients for a given period """

    context = {
        'page_title': 'Generate Reports',
        'form_title': 'Generate all configured reports',
        'form_subtitle': 'NB! This process can take up to 5 minutes',
        'form_address': '/reports/generate/period-all/',
        'form': PeriodForm()
    }

    if request.method == 'POST':
        form = PeriodForm(request.POST)
        if form.is_valid():
            period = form.cleaned_data.get('period')
            async_result = m.gen_reports.delay(period)
            context = {
                'list_title': f'Generating report for all clients for {period}',
                'list_subtitle': 'This could take up to 5 minutes',
                'taskId': async_result.id
            }
            return render(request, 'shared/processing_bar.html', context)
        else:
            context['form'] = form

    return render(request, 'shared/base_form.html', context)


def render_period_client(request):
    """ Triggers the rendering of report for one client for a given period """

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
            if client and period:
                async_result = m.gen_report_for_client.delay(period, client.client_id)
                context = {
                    'list_title': f'Generating report for {client.reporting_name}',
                    'taskId': async_result.id
                }
                return render(request, 'shared/processing_bar.html', context)
        else:
            context['form'] = form
    return render(request, 'shared/base_form.html', context)


def render_period_report(request):
    """ Triggers the rendering of a specific report for a given period """

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
                async_result = m.gen_report_by_id.delay(period, report.id)
                context = {
                    'list_title': f'Generating report {report.file_name}',
                    'taskId': async_result.id
                }
                return render(request, 'shared/processing_bar.html', context)
        else:
            context['form'] = form
    return render(request, 'shared/base_form.html', context)


# BILLING REPORTS DOWNLOAD
def download_billing_report(request, pk: int):
    """ Triggers download of a billing report file with the given pk """

    try:
        report_file = ReportFile.objects.get(pk=pk)
        filepath = report_file.file.path
        logger.debug(f'Requested file to download: {filepath}')
        response = download_excel_file(filepath)
        response["Cache-Control"] = "no-store"
        return response

    except ReportFile.DoesNotExist:
        logger.warning(f'Does Not Exist: ReportFile with id {pk}')
        return HttpResponse('No report file with such id')


def download_billing_reports_all(request, period: str):
    """ Triggers the download of a ZIP archive with all billing report files for a given period """

    queryset = ReportFile.objects.filter(period=period)
    response = create_zip_file(queryset, f'{period}_billing_reports')
    response["Cache-Control"] = "no-store"
    return response


def list_report_files(request):
    """ Visualize PeriodForm to trigger list of billing report files """

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
            files = ReportFile.objects.filter(period=period, type_id=1).order_by('report__client_id')
            context = {
                'header': f'List of billing report files for {period}',
                'files': files,
                'zip_url': reverse('download_billing_reports_all', args=[period]),
                'list_url': 'download_billing_report'
            }
            return render(request, 'shared/file_download_list.html', context)
    return render(request, 'shared/base_form.html', context)


def reconciliation(request):
    vs = VendorService.objects.filter(
        vendor__client__is_billable=True,
        vendor__client__is_validated=True,
        orderservice__isnull=True
    ).values_list('vendor_id', 'service_id', 'service__service', 'service__stype', 'service__desc_en')
    vendor_services = [f'Vendor {el[0]} - Service {" ".join(str(x) for x in el[1:])}' for el in vs]

    billable_vendors = set(el.vendor for el in VendorService.objects.filter(
        vendor__client__is_billable=True,
        vendor__reports__isnull=True
    ))
    billable_clients_no_report = [el for el in Client.objects.filter(
        is_billable=True,
        reports__isnull=True
    )]
    billable_clients_not_validated = [el for el in Client.objects.filter(
        is_billable=True,
        is_validated=False
    )]
    usage_stats_check = [f'{el.period} Vendor {el.vendor} - Service {el.service}' for el in get_su()]

    context = {
        'res_details': {
            (0, 'Accounts not assigned to clients'): [el for el in Vendor.objects.filter(client_id=0)],
            (1, 'Accounts not reconciled'): [el for el in Vendor.objects.filter(is_reconciled=False)],
            (2, 'Accounts with usage that are not assigned to reports'): billable_vendors,
            (3, 'UsageStats without corresponding AccountService configuration'): usage_stats_check,
            (4, 'AccountService configuration not assigned to orders'): vendor_services,
            (5, 'Billable clients marked as not-validated'): billable_clients_not_validated,
            (6, 'Billable clients without reports'): billable_clients_no_report,
        }
    }
    return render(request, 'shared/results_collapse.html', context)


def _download_report(filepath):
    with open(filepath, 'rb') as f:
        response = HttpResponse(f.read(), content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename={}'.format(os.path.basename(filepath))
        return response
