from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.ClientsListView.as_view(), name='clients_list'),
    path('<int:pk>/', include([
        path('details/', views.ClientDetailsView.as_view(template_name='client_details.html'), name='client_details'),
        path('contracts/',
             views.ClientDetailsView.as_view(template_name='client_contracts.html'), name='client_contracts'),
        path('accounts/', views.ClientDetailsView.as_view(template_name='client_accounts.html'), name='client_accounts'),
    ])),
]
