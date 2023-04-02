from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


from .forms import VendorPeriodForm, PeriodForm, FileUploadForm
from .models import Vendor, VendorInputFile
from .modules import recalc_vendor, recalc_all_vendors, \
    handle_uploaded_file, list_archive, handle_extract_zip, delete_inactive_input_files


@login_required
def index(request):
    return render(request, 'vendors_index.html')


@login_required
def res_result(res_id):
    """ Return verbose names for the results of the calc_vendor functions """
    update_vendor_legend = {
        0: 'Complete',
        1: 'No services configured',
        2: 'No input file',
        3: 'No transactions',
        4: 'Not reconciled'
    }
    return update_vendor_legend.get(res_id, 'Not defined')


@login_required
def calc_vendor_usage(request):
    context = {
        'page_title': 'Calculate Usage',
        'form_title': 'Calculate usage for a vendor_id',
        'form_address': '/vendors/calc-vendor/',
        'form': VendorPeriodForm()
    }
    if request.method == 'POST':
        form = VendorPeriodForm(request.POST)
        context['form'] = form
        if form.is_valid():
            period = form.cleaned_data.get('period')
            vendor_id = form.cleaned_data.get('pk', None)
            if vendor_id is not None:
                res = recalc_vendor(period, int(vendor_id))
                if res:
                    cv_dict = {k: v for k, v in Vendor.objects.values_list('vendor_id', 'description')}
                    k, v = res
                    context['res_details'] = {(k, res_result(k)): [f'{v} - {cv_dict[v]}']}
                return render(request, 'results_collapse.html', context)
    return render(request, 'base_form.html', context)


@login_required
def calc_usage_all_vendors(request):
    context = {
        'page_title': 'Calculate Usage',
        'form_title': 'Calculate usage for all vendor_id',
        'form_address': '/vendors/calc-all/',
        'form': PeriodForm()
    }
    if request.method == 'POST':
        form = PeriodForm(request.POST)
        context['form'] = form
        if form.is_valid():
            period = form.cleaned_data.get('period')
            res = recalc_all_vendors(period)
            if res:
                cv_dict = {k: v for k, v in Vendor.objects.values_list('vendor_id', 'description')}
                res_details = {(k, res_result(k)): [f'{el} - {cv_dict[el]}' for el in v] for k, v in res.items()}
                context['res_details'] = res_details
            return render(request, 'results_collapse.html', context)
    return render(request, 'base_form.html', context)


@login_required
def list_vendor_files(request):
    context = {
        'page_title': 'Manage Vendor Files',
        'form_title': 'List vendor input files',
        'form_address': '/vendors/view-files/',
        'form': PeriodForm()
    }
    if request.method == 'POST':
        form = PeriodForm(request.POST)
        context['form'] = form
        if form.is_valid():
            period = form.cleaned_data.get('period')
            return redirect('list_vendor_files_period', period)
    return render(request, 'base_form.html', context)


@login_required
def list_vendor_files_period(request, period):
    files = VendorInputFile.objects.filter(period=period, is_active=True).order_by('vendor')
    if files.exists():
        context = {'files': files}
        return render(request, 'vendor_file_download.html', context)
    return HttpResponse('No vendor files for this period')


@login_required
def upload_zip(request):
    context = {
        'page_title': 'Vendor Input ZIP',
        'form_title': 'File Upload',
        'form_subtitle': 'Upload zip-file with vendor input files for a given period',
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


@login_required
def extract_zip(request):
    """ Extract the contents of the last uploaded Iteco achive """

    # Get the content of the last uploaded archive
    zip_content = list_archive()

    if zip_content is None:
        return HttpResponse("No zip file found!")
    elif len(zip_content) == 0:
        return HttpResponse("No valid data in ZIP file.")
    else:
        context = {
            'page_title': 'Extract Vendor Input ZIP',
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
                    'page_title': 'Extract Vendor Input ZIP',
                    'report_title': 'Processed vendors',
                    'res_details': res
                }
                return render(request, 'results_collapse.html', context)
        return render(request, 'result_zip_upload.html', context)


@login_required
def delete_unused_vendor_input_files(request):
    deleted_files = delete_inactive_input_files()
    return HttpResponse(deleted_files)
