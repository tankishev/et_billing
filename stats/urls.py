from django.urls import path, include
from . import views

urlpatterns = [
    path('test/', views.stats_test, name='stats_test'),
    path('uqu/', include([
        path('save/', include([
            path('', views.save_unique_users, name='uqu_save'),
            path('clients/', views.save_unique_users_clients, name='uqu_save_clients'),
            path('periods/', views.save_unique_users_periods, name='uqu_save_periods'),
            path('vendors/', views.save_unique_users_vendors, name='uqu_save_vendors'),
        ])),
        path('view/', views.view_unique_users, name='uqu_view'),
    ])),
]
