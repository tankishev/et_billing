# TO DELETE TEST URLS
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='vendors_index'),

    # Processing fo vendor files
    path('delete-unused/', views.delete_unused_vendor_input_files, name='vendor_files_delete_unused'),
    path('download/', include([
        path('all/<str:period>/', views.download_vendor_files_all, name='download_vendor_files_all'),
        path('file/<int:pk>/', views.download_vendor_file, name='download_vendor_file'),
    ])),
    path('view-files/', views.list_vendor_files, name='list_vendor_files'),

    # Processing of zip files
    path('extract/', views.extract_zip_view, name='vendor_zip_extract'),
    path('upload/', views.upload_zip_view, name='vendor_zip_upload'),
    path('upload-file/', views.upload_single_file, name='vendor_file_upload'),
]
