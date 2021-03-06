"""
Django settings for reports project.

Generated by 'django-admin startproject' using Django 1.11.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import configparser


# Настраиваем логирование
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(name)s %(funcName)s: %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/django.log',
            'formatter': 'verbose',

        },
    },
    'loggers': {
        'audit': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '#z9g5m**p87_lds4!a@@_=drp!eo#&c=oeyvxcb$8vokk9=r0u'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['10.0.3.249', 'django', '192.168.128.43', '10.0.3.16']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'documents.apps.DocumentsConfig',
    'audit.apps.AuditConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    # http://django-debug-toolbar.readthedocs.io/en/stable/
    INTERNAL_IPS = ('127.0.0.1', 'localhost', '10.0.3.1')
    MIDDLEWARE += (
       'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

    INSTALLED_APPS += (
       'debug_toolbar',
       'debug_toolbar_line_profiler',
    )

    DEBUG_TOOLBAR_PANELS = [
       # 'debug_toolbar.panels.versions.VersionsPanel',
       'debug_toolbar.panels.timer.TimerPanel',
       # 'debug_toolbar.panels.settings.SettingsPanel',
       # 'debug_toolbar.panels.headers.HeadersPanel',
       # 'debug_toolbar.panels.request.RequestPanel',
       'debug_toolbar.panels.sql.SQLPanel',
       # 'debug_toolbar.panels.staticfiles.StaticFilesPanel',
       # 'debug_toolbar.panels.templates.TemplatesPanel',
       'debug_toolbar.panels.cache.CachePanel',
       # 'debug_toolbar.panels.signals.SignalsPanel',
       # 'debug_toolbar.panels.logging.LoggingPanel',
       # 'debug_toolbar.panels.redirects.RedirectsPanel',
       'debug_toolbar.panels.profiling.ProfilingPanel',
       # 'debug_toolbar_line_profiler.panel.ProfilingPanel',
    ]
    DEBUG_TOOLBAR_CONFIG = {
       'INTERCEPT_REDIRECTS': False,
    }

ROOT_URLCONF = 'reports.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'reports.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
# Берём данные из конфига /etc/django_reports.conf (что бы не коммитить пароли)
# Пример конфига в reports/django_reports.conf
file_config = '/etc/django_reports.conf'
if not os.path.isfile(file_config):
    # Если файл с конфигом отсутствует, то берём данные из примера
    file_config = 'reports/django_reports.conf'

config = configparser.ConfigParser()
config.read(file_config)

DATABASES = {
    'default': {
        key.upper(): config['DJANGO_DB'][key] for key in config['DJANGO_DB']
    }
}
# Параметры базы CRM для audit/externeldb.py
if 'CRM_DB' in config:
    DATABASES_CRM = {
        key: config['CRM_DB'][key] for key in config['CRM_DB']
    }

# Параметры базы UTM для audit/externeldb.py
if 'UTM_DB' in config:
    DATABASES_UTM = {
        key: config['UTM_DB'][key] for key in config['UTM_DB']
    }

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

# TIME_ZONE = 'UTC'
TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = '/home/bud/django/static/'

# Настраиваем КЭШ
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/django_cache',
    }
}

# URL для авторизации
LOGIN_URL = '/audit/login/'
