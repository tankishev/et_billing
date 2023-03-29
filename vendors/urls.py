from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='vendors_index'),
    path('calc-vendor/', views.calc_vendor_usage, name='calc_vendor_usage'),
    path('calc-all/', views.calc_usage_all_vendors, name='calc_usage_all'),
    path('view-files/', include([
        path('', views.list_vendor_files, name='list_vendor_files'),
        path('<str:period>/', views.list_vendor_files_period, name='list_vendor_files_period')
    ])),
    path('upload/', views.upload_zip, name='vendor_zip_upload'),
    path('extract/', views.extract_zip, name='vendor_zip_extract'),
    path('delete-unused/', views.delete_unused_vendor_input_files, name='vendor_files_delete_unused'),
]
