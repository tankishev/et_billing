# ADD LOGGERS
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import UniqueUsersForm
from .modules import get_uqu, store_uqu_celery


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
