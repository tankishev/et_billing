from django.urls import path
from . import views

urlpatterns = [
    path('', views.PackageView.as_view(template_name='prepaidpackages_list.html')),
]
