from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .forms import UniqueUsersForm, VendorPeriodForm, PeriodForm
from .modules.uq_users import get_uqu, store_uqu_celery
from .modules.usage_calculations import recalc_vendor, recalc_all_vendors, get_vendor_unreconciled

import logging
logger = logging.getLogger('et_billing.stats.views')


# SERVICE USAGE CALCULATIONS
@login_required
def calc_service_usage(request):
    """ Trigger usage calculation for one account """

    context = {
        'page_title': 'Calculate Usage',
        'form_title': 'Calculate usage for an account',
        'form_subtitle': None,
        'form_address': '/stats/usage/calc-account/',
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
def calc_service_usage_all_vendors(request):
    """ Trigger usage calculation for all vendor """

    context = {
        'page_title': 'Calculate Usage',
        'form_title': 'Calculate usage for ALL accounts',
        'form_subtitle': None,
        'form_address': '/stats/usage/calc-all/',
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


# UNIQUE USERS CALCULATIONS
@login_required
def view_unique_users(request):
    """ Renders a form for generating reports on unique users """

    form = UniqueUsersForm()
    context = {
        'form_title': 'Get unique users'
    }
    if request.method == 'POST':
        form = UniqueUsersForm(request.POST)
        if form.is_valid():
            # Collect user input
            entity_scope = form.cleaned_data.get('scope_select')
            period_scope = form.cleaned_data.get('period_select')
            client = None if entity_scope == '2' else form.cleaned_data.get('client')
            client_id = client.client_id if client is not None else None
            period_start = None if period_scope == '3' else form.cleaned_data.get('period_start')
            period_end = form.cleaned_data.get('period_end') if period_scope == "2" else None

            # Generate report
            res = get_uqu(client_id, period_start, period_end)
            context.update({'uqu_res': f'{res:,}'})

    context.update({'form': form})
    return render(request, 'unique_users.html', context)


@login_required
def save_unique_users_celery(request):
    """ Trigger calculation of unique users """

    async_result = store_uqu_celery.delay()
    context = {
        'list_title': 'Calculate statistics for unique users',
        'list_subtitle': 'This could take up to 5 minutes',
        'taskId': async_result.id
    }
    return render(request, 'processing_bar.html', context)
