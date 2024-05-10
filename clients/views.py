from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from .models import Client, Industry, ClientCountry
from reports.models import ReportSkipColumnConfig, ReportLanguage


# Create your views here.
class ClientsListView(ListView):
    queryset = Client.objects.all().order_by('reporting_name')
    template_name = 'clients/clients_list.html'
    paginate_by = 15


class ClientDetailsView(DetailView):
    model = Client

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['industries'] = Industry.objects.all()
        context['countries'] = ClientCountry.objects.all()
        context['skip_configs'] = ReportSkipColumnConfig.objects.all()
        context['report_languages'] = ReportLanguage.objects.all()
        return context
