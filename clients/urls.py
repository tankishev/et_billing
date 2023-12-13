from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.ClientsListView.as_view(), name='clients_list'),
    path('<int:pk>/', include([
        path('details/', views.ClientDetailsView.as_view(template_name='clients/client_details.html'), name='client_details'),
        path('contracts/',
             views.ClientDetailsView.as_view(template_name='clients/client_contracts.html'), name='client_contracts'),
        path('accounts/', views.ClientDetailsView.as_view(template_name='clients/client_accounts.html'), name='client_accounts'),
        path('reports/', views.ClientDetailsView.as_view(template_name='clients/client_reports.html'), name='client_reports'),
        path('issues/', views.ClientDetailsView.as_view(template_name='clients/client_issues.html'), name='client_issues'),
    ])),
]
