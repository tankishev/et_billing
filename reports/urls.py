from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='reports_index'),
    path('generate/', include([
        path('period-all/', views.render_period, name='period_report'),
        path('period-client/', views.render_period_client, name='period_client_report'),
        path('period-single/', views.render_period_report, name='period_report_id'),
        path('zoho-service-usage/', views.zoho_service_usage, name='zoho_service_usage_report'),
    ])),
    path('view-files/', include([
        path('', views.list_report_files, name='list_report_files'),
    ])),
    path('download/', include([
        path('zoho/<str:period>/<str:filename>/', views.download_zoho_report, name='download_zoho_report'),
        path('billing/file/<int:pk>/', views.download_billing_report, name='download_billing_report'),
        path('billing/all/<str:period>/', views.download_billing_reports_all, name='download_billing_reports_all'),
    ])),
    path('reconciliation/', views.reconciliation, name='db_reconciliation'),
    path('test/', views.reports_test, name='reports_test'),
]
