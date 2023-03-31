from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('admin/', admin.site.urls),
    path("reports/", include('reports.urls')),
    path("vendors/", include('vendors.urls')),
    path("stats/", include('stats.urls')),
    path("packages/", include('packages.urls')),
    path("accounts/", include("django.contrib.auth.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
