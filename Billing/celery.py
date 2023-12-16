from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.signals import setup_logging
from django.conf import settings


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Billing.settings')

app = Celery('Billing')

app.config_from_object("django.conf:settings", namespace="CELERY")

# Use the Redis broker.
app.conf.broker_url = 'redis://localhost:6379/0'

# Using the django-celery-results backend to store task results
app.conf.result_backend = None


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig  # noqa
    from django.conf import settings  # noqa

    dictConfig(settings.LOGGING)


# Automatically discover tasks from your installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
