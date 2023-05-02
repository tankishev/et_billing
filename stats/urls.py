from django.urls import path, include
from . import views

urlpatterns = [
    path('test/', views.stats_test, name='stats_test'),
    path('uqu/', include([
        path('save/', views.save_unique_users_celery, name='uqu_save'),
        path('view/', views.view_unique_users, name='uqu_view'),
    ])),
]
