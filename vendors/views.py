# CODE OK
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from shared.views import download_excel_file
from shared.modules import create_zip_file
from .forms import VendorPeriodForm, PeriodForm, FileUploadForm
from .models import VendorInputFile
from .modules import recalc_vendor, recalc_all_vendors, get_vendor_unreconciled, \
    handle_uploaded_file, list_archive, handle_extract_zip, delete_inactive_input_files

import logging

logger = logging.getLogger('et_billing.vendors.views')


@login_required
def index(request):
    return render(request, 'vendors_index.html')


# VENDOR USAGE CALCULATIONS
@login_required
def calc_vendor_usage(request):
    """ Trigger usage calculation for one account """

    context = {
        'page_title': 'Calculate Usage',
        'form_title': 'Calculate usage for an account',
        'form_subtitle': None,
        'form_address': '/vendors/calc-vendor/',
        'form': VendorPeriodForm()
    }

    if request.method == 'POST':
        form = VendorPeriodForm(request.POST)
        if form.is_valid():
            period = form.cleaned_data.get('period')
            vendor_id = form.cleaned_data.get('pk', None)
            if vendor_id is not None:
                async_result = recalc_vendor.delay(period, int(vendor_id))
                context = {
                    'list_title': f'Calculate usage for account {vendor_id}',
                    'taskId': async_result.id
                }
                return render(request, 'processing_bar.html', context)
        else:
            context['form'] = form

    return render(request, 'base_form.html', context)


@login_required
def calc_usage_all_vendors(request):
    """ Trigger usage calculation for all vendor """

    context = {
        'page_title': 'Calculate Usage',
        'form_title': 'Calculate usage for ALL accounts',
        'form_subtitle': None,
        'form_address': '/vendors/calc-all/',
        'form': PeriodForm()
    }

    if request.method == 'POST':
        form = PeriodForm(request.POST)
        if form.is_valid():
            period = form.cleaned_data.get('period')
            async_result = recalc_all_vendors.delay(period)
            context = {
                'list_title': 'Calculate usage for ALL accounts',
                'list_subtitle': 'This could take up to 2 minutes',
                'taskId': async_result.id
            }
            return render(request, 'processing_bar.html', context)
        else:
            context['form'] = form

    return render(request, 'base_form.html', context)


def view_unreconciled_transactions(request, file_id: int):
    """ Return transactions and possible services for the Unreconciled modal """

    res = get_vendor_unreconciled(file_id)
    return JsonResponse(res, safe=False)


# PROCESSING OF VENDOR INPUT FILES
@login_required
def delete_unused_vendor_input_files(request):
    """ Triggers deletion of VendorInputFiles marked as inactive """

    deleted_files = delete_inactive_input_files()
    return HttpResponse(deleted_files)


@login_required
def download_vendor_file(request, pk: int):
    """ Triggers download of a vendor file with the given pk """

    try:
        file = VendorInputFile.objects.get(pk=pk)
        filepath = file.file.path
        logger.debug(f'Requested file to download: {filepath}')
        return download_excel_file(filepath)

    except VendorInputFile.DoesNotExist:
        logger.warning(f'Does Not Exist: VendorInputFile with id {pk}')
        return HttpResponse('No account file with such id')


@login_required
def download_vendor_files_all(request, period: str):
    """ Triggers the download of a ZIP archive with all vendor input files for a given period """

    queryset = VendorInputFile.objects.filter(period=period)
    return create_zip_file(queryset, f'{period}_vendor_files')


@login_required
def extract_zip_view(request):
    """ Extract the contents of the last uploaded vendor input ZIP archive """

    # Get the content of the last uploaded archive
    zip_content = list_archive()

    if zip_content is None:
        return HttpResponse("No zip file found!")
    elif len(zip_content) == 0:
        return HttpResponse("No valid data in ZIP file.")
    else:
        context = {
            'page_title': 'Extract Account Usage ZIP Archive',
            'form_address': '/vendors/extract/',
            'form': PeriodForm(initial={'period': request.session.get('upload_period')}),
            'report_title': 'Archive Contents',
            'res_details': {(0, 'Files in archive'): zip_content},
            'res_action': True
        }
        if request.method == 'POST':
            form = PeriodForm(request.POST)
            context['form'] = form
            if form.is_valid():
                period = form.cleaned_data.get('period')
                res = handle_extract_zip(period)
                context = {
                    'page_title': 'Extract Account Usage ZIP Archive',
                    'report_title': 'Processed accounts',
                    'res_details': res
                }
                return render(request, 'results_collapse.html', context)
        return render(request, 'result_zip_upload.html', context)


@login_required
def list_vendor_files(request):
    """ Visualize PeriodForm to trigger list of vendor files """

    context = {
        'page_title': 'Manage Account Usage Files',
        'form_title': 'List account usage files',
        'form_address': '/vendors/view-files/',
        'form': PeriodForm()
    }
    if request.method == 'POST':
        form = PeriodForm(request.POST)
        context['form'] = form
        if form.is_valid():
            period = form.cleaned_data.get('period')
            files = VendorInputFile.objects.filter(period=period, is_active=True).order_by('vendor')
            context = {
                'header': f'List of account usage files for {period}',
                'files': files,
                'zip_url': reverse('download_vendor_files_all', args=[period]),
                'list_url': 'download_vendor_file'
            }
            return render(request, 'file_download_list.html', context)
    return render(request, 'base_form.html', context)


@login_required
def upload_zip_view(request):
    """ Load form for uploading a Vendor Input ZIP archive and trigger extraction if file is valid """

    context = {
        'page_title': 'Account Usage ZIP Archive',
        'form_title': 'File Upload',
        'form_subtitle': 'Upload zip-file with account usage files for a given period',
        'form_address': '/vendors/upload/',
        'form_enctype': "multipart/form-data",
        'form': FileUploadForm()
    }
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        context['form'] = form
        if form.is_valid():
            file = request.FILES['file']
            z_file = handle_uploaded_file(file)
            if z_file is not None:
                period = form.cleaned_data.get('period')
                request.session['upload_period'] = period
                return redirect('vendor_zip_extract')
            context['err_message'] = f'Attached file must be a valid ZIP file.'
    return render(request, 'base_form.html', context)
