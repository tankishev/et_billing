from django.http import HttpResponse
from django.shortcuts import render

from shared.forms import PeriodForm
from .forms import UniqueUsersForm
from .models import UniqueUser
from .modules import store_unique_users

from reports.modules import gen_zoho_uqu_period, gen_zoho_uqu_clients, gen_zoho_uqu_vendors

from .modules.uq_users import store_uqu_client, store_uqu_vendors, store_uqu_periods


def lyubo_test(request):
    if request.method == 'POST':
        form = PeriodForm(request.POST)
        if form.is_valid():
            period = form.cleaned_data.get('period')
            res = gen_zoho_uqu_vendors(period)
            return HttpResponse(res.to_html())
    form = PeriodForm()
    return render(request, 'base_form.html', {'form': form})


def view_unique_users(request):
    form = UniqueUsersForm()
    context = {
        'form_title': 'Get unique users'
    }
    if request.method == 'POST':
        form = UniqueUsersForm(request.POST)
        if form.is_valid():
            entity_scope = form.cleaned_data.get('scope_select')
            period_scope = form.cleaned_data.get('period_select')
            client = None if entity_scope == '2' else form.cleaned_data.get('client')
            client_id = client.client_id if client is not None else None
            period_start = None if period_scope == '3' else form.cleaned_data.get('period_start')
            period_end = form.cleaned_data.get('period_end') if period_scope == "2" else None
            res = get_uqu(client_id, period_start, period_end)
            context.update({'uqu_res': f'{res:,}'})

    context.update({'form': form})
    return render(request, 'unique_users.html', context)
    # return store_unique_users()
    # return get_uqu_vendors_periods([7, 153], '2023-01', '2023-01')
    # return get_uqu_periods('2023-01', '2023-01')
    # return remove_unique_users('2023-01')


def save_unique_users(request):
    res = store_unique_users()
    context = {'res_details': {(0, 'Processed files'): res}}
    return render(request, 'results_collapse.html', context)


def read_unique_users(request):
    unique_users = UniqueUser.objects.filter(month='2020-02')
    return HttpResponse(unique_users)


def get_uqu_data():
    uqu_data = UniqueUser.objects.values('month', 'vendor_id').distinct()
    return HttpResponse(len(uqu_data.filter(month='2020-10')) > 0)


def remove_unique_users(period):
    UniqueUser.objects.filter(month=period).delete()
    return HttpResponse('OK')


def get_uqu(client_id=None, start_period=None, end_period=None):
    if client_id is None:
        if start_period is None and end_period is None:
            uqu_data = UniqueUser.objects.all().values_list('user_id', flat=True).distinct()
        elif end_period is None:
            uqu_data = UniqueUser.objects.filter(month__range=[start_period, start_period]) \
                .values_list('user_id', flat=True).distinct()
        else:
            uqu_data = UniqueUser.objects.filter(month__range=[start_period, end_period]) \
                .values_list('user_id', flat=True).distinct()
    else:
        if start_period is None and end_period is None:
            uqu_data = UniqueUser.objects.filter(vendor__client__client_id=client_id) \
                .values_list('user_id', flat=True).distinct()
        elif end_period is None:
            uqu_data = UniqueUser.objects\
                .filter(vendor__client__client_id=client_id, month__range=[start_period, start_period]) \
                .values_list('user_id', flat=True).distinct()
        else:
            uqu_data = UniqueUser.objects\
                .filter(vendor__client__client_id=client_id, month__range=[start_period, end_period]) \
                .values_list('user_id', flat=True).distinct()
    return len(uqu_data)
