from django.urls import path, include

from . import views

urlpatterns = [
    path('', include([
        path('accounts/', include([
            path('calculate-usage/', views.vendor_calculate_usage),
            path('list/', views.vendors_list),
            path('<int:pk>/', include([
                path('', views.vendor_details),
                path('duplicate-services/', views.vendor_services_duplicate),
                path('services/', include([
                    path('', views.vendor_services, name='get_vendor_services'),
                    path('add/', views.vendor_services_add),
                    path('remove/', views.vendor_services_remove),
                ])),
            ])),
        ])),
        path('clients/', include([
            path('', views.clients_list),
            path('<int:pk>/', include([
                path('', views.client_details),
                path('accounts/', views.client_vendors),
                path('issues/', views.health_check),
                path('reports/', include([
                    path('create/', views.client_create_report),
                    path('files/', views.client_report_files_list),
                    path('list/', views.client_reports_list),
                ])),
                path('services/', views.client_services),
            ])),
        ])),
        path('contracts/', include([
            path('', views.contracts_list),
            path('<int:pk>/', include([
                path('', views.contract_details),
                path('orders/', views.contract_orders),
            ])),
        ])),
        path('orders/', include([
            path('', views.orders_list),
            path('<int:pk>/', include([
                path('', views.order_details),
                path('duplicate/', views.order_duplicate),
                path('prices/', views.order_service_prices),
                path('services/', include([
                    path('', views.order_services, name='get_order_services'),
                    path('add/', views.order_services_add),
                    path('remove/', views.order_services_remove),
                ])),
            ])),
        ])),
        path('order-service/<int:pk>/', views.order_service_edit),
        path('reports/', include([
            path('<int:pk>/', include([
                path('', views.report_details),
                path('assign-accounts/', views.report_update_vendors),
            ])),
            path('generate/', include([
                path('client/', views.report_render_period_client),
                path('report/', views.report_render_period_report),
            ])),
        ])),
        path('tasks/', include([
            path('', views.get_task_list),
            path('<str:task_id>/', views.get_task_progress),
        ])),
        path('metadata/', views.get_metadata),
    ])),
]
