# REMOVE DEPRECIATED IMPORTS ... ADD LOGGERS
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from reports.modules import gen_zoho_uqu_vendors
from shared.forms import PeriodForm
from .forms import UniqueUsersForm
from .modules import store_unique_users, get_uqu
from .modules import store_uqu_clients, store_uqu_vendors, store_uqu_periods

# from .models import UniqueUser


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
def save_unique_users(request):
    """ Triggers saving of UniqueUser stats """

    res = store_unique_users()
    context = {'res_details': {(0, 'Processed files'): res}}
    return render(request, 'results_collapse.html', context)


@login_required
def save_unique_users_periods(request):
    """ Triggers saving of UquStatsPeriod aggregate stats """

    store_uqu_periods()
    return redirect('home')


@login_required
def save_unique_users_clients(request):
    """ Triggers saving of UquStatsPeriod aggregate stats """

    store_uqu_clients()
    return redirect('home')


@login_required
def save_unique_users_vendors(request):
    """ Triggers saving of UquStatsPeriod aggregate stats """

    store_uqu_vendors()
    return redirect('home')


# REMOVE TEST AND DEPRECIATE
@login_required
def stats_test(request):
    if request.method == 'POST':
        form = PeriodForm(request.POST)
        if form.is_valid():
            period = form.cleaned_data.get('period')
            res = gen_zoho_uqu_vendors(period)
            return HttpResponse(res.to_html())
    form = PeriodForm()
    return render(request, 'base_form.html', {'form': form})

# def remove_unique_users(period):
#     UniqueUser.objects.filter(month=period).delete()
#     return HttpResponse('OK')
