from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path("et_auth/", views.index, name='et_auth'),
    path("accounts/", include('accounts.urls')),
    path('admin/', admin.site.urls),
    path("reports/", include('reports.urls')),
    path("vendors/", include('vendors.urls')),
    path("stats/", include('stats.urls')),
    path("tasks/", include('celery_tasks.urls')),
    path("packages/", include('packages.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
