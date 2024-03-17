from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from . import views
from billing_module.views import debug_view

urlpatterns = [
    path('', views.index, name='home'),
    path("et_auth/", views.index, name='et_auth'),
    path("accounts/", include('accounts.urls')),
    path('admin/', admin.site.urls),
    path("reports/", include('reports.urls')),
    path("vendors/", include('vendors.urls')),
    path("stats/", include('stats.urls')),
    path("tasks/", include('celery_tasks.urls')),
    path("clients/", include('clients.urls')),
    path("api/", include('api.urls')),
    path("debug/", debug_view),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
