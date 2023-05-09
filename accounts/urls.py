from django.contrib.auth.views import LogoutView
from django.urls import path, include
from . import views


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', include("django.contrib.auth.urls")),
]
