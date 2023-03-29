from django.urls import path, include
from . import views

urlpatterns = [
    path('test/', views.lyubo_test, name='lyubo_test'),
    path('uqu/save/', views.save_unique_users, name='uqu_save'),
    path('uqu/save/', views.view_unique_users, name='uqu_view'),
]

