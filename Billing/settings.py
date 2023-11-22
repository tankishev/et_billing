"""
Django settings for Billing project.

Generated by 'django-admin startproject' using Django 4.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path
import logging.config
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environmental variables
load_dotenv()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = (os.environ.get('DJANGO_DEBUG').lower() == 'true')

ALLOWED_HOSTS = ['127.0.0.1', '85.196.148.19']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'clients.apps.ClientsConfig',
    'services.apps.ServicesConfig',
    'vendors.apps.VendorsConfig',
    'reports.apps.ReportsConfig',
    'contracts.apps.ContractsConfig',
    'stats.apps.StatsConfig',
    'packages.apps.PackagesConfig',
    'celery_tasks.apps.CeleryTasksConfig',
    'accounts.apps.AccountsConfig'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.RequireLoginMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Billing.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Billing.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('PG_DB_NAME'),
        'USER': os.environ.get('PG_USERNAME'),
        'PASSWORD': os.environ.get('PG_PASSWORD'),
        'HOST': os.environ.get('PG_HOST'),
        'PORT': os.environ.get('PG_HOST_PORT')
    }
}

if DEBUG:
    from sshtunnel import SSHTunnelForwarder

    # Connect to a server using the ssh keys. See the sshtunnel documentation for using password authentication
    ssh_tunnel = SSHTunnelForwarder(
        (os.environ.get('PG_SSH_HOST'), int(os.environ.get('PG_SSH_PORT'))),
        ssh_pkey=os.environ.get('PG_SSH_KEY'),
        ssh_private_key_password=os.environ.get('PG_SSH_PASS'),
        ssh_username=os.environ.get('PG_SSH_USER'),
        remote_bind_address=('127.0.0.1', int(os.environ.get('PG_HOST_PORT'))),
    )
    ssh_tunnel.start()
    DATABASES['default']['PORT'] = ssh_tunnel.local_bind_port

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# LOGIN_REDIRECT_URL = '/'

# Session timeouts
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True

# Session cookies
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'Strict'

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'static/'
# STATIC_ROOT = os.path.join(BASE_DIR, 'static')
# STATIC_ROOT = BASE_DIR / 'static'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery settings
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = None
CELERY_HIJACK_ROOT_LOGGER = False

# Settings for logging
LOG_DIR = os.environ.get('DJANGO_LOGS_DIR', os.path.join(BASE_DIR, 'logs'))
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # retain the default loggers
    'formatters': {
        'pipe': {
            'format': '{asctime}|{module}|{levelname}|{message}',
            'style': '{',
        },
    },
    'handlers': {
        'et_billing_debug': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'et_billing_debug.log'),
            'formatter': 'pipe',
            'level': 'DEBUG'
        },
        'celery_tasks_debug': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'celery_debug.log'),
            'formatter': 'pipe',
            'level': 'DEBUG'
        },
        'et_billing_info': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'et_billing_info.log'),
            'formatter': 'pipe',
            'level': 'INFO'
        },
        'celery_tasks_info': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'celery_info.log'),
            'formatter': 'pipe',
            'level': 'INFO'
        },
    },
    'loggers': {
        'et_billing': {
            'level': 'DEBUG',
            'handlers': ['et_billing_debug', 'et_billing_info'],
            'propagate': False
        },
        'celery.task': {
            'level': 'DEBUG',
            'handlers': ['celery_tasks_debug', 'celery_tasks_info'],
            'propagate': False
        },
    }
}
