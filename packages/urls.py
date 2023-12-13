from django.urls import path
from . import views

urlpatterns = [
    path('', views.PackageView.as_view(template_name='packages/prepaid_packages_list.html')),
]
