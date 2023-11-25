from django.urls import path, include
from . import views

urlpatterns = [
    path('', include([
        path('accounts/', include([
            path('list/', views.vendors_list),
            path('<int:pk>/', include([
                path('', views.vendor_details),
                path('services/', include([
                    path('', views.vendor_services, name='get_vendor_services'),
                    path('add/', views.vendor_services_add),
                    path('remove/', views.vendor_services_remove),
                ])),
                path('duplicate-services/', views.vendor_services_duplicate),
            ])),
        ])),
        path('clients/', include([
            path('', views.clients_list),
            path('<int:pk>/', include([
                path('', views.client_details),
                path('accounts/', views.client_vendors),
                path('issues/', views.health_check),
                path('reports/', views.client_reports_list),
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
        path('metadata/', views.get_metadata),
    ])),
]
