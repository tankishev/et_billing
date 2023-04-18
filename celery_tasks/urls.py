from django.urls import path
from . import views

urlpatterns = [
    path('task_status/<str:task_id>/', views.get_task_progress, name='get-task-progress'),
]
