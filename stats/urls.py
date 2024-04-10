from django.urls import path, include
from . import views


urlpatterns = [
    # Usage calculations
    path('usage/', include([
        path('calc-all/', views.calc_service_usage_all_vendors, name='calc_usage_all'),
        path('calc-account/', views.calc_service_usage, name='calc_vendor_usage'),
        path('get-unreconciled/<int:file_id>/', views.view_unreconciled_transactions, name='get_unreconciled'),
        path('load-all/', views.load_usage_transactions_all, name='load_usage_transactions_all'),
        path('rate-all/', views.rate_usage_transactions_all_accounts, name='rate_usage_transactions_all'),
    ])),
    path('uqu/', include([
        path('save/', views.save_unique_users_celery, name='uqu_save'),
        path('view/', views.view_unique_users, name='uqu_view'),
    ])),
]
