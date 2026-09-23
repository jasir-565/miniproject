"""Disposable MySQL integration database. Never uses local_settings.json credentials."""
import os
from .test_settings import *  # noqa: F403

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'autonexa_ci',
    'USER': os.environ.get('MYSQL_TEST_USER', 'root'),
    'PASSWORD': os.environ['MYSQL_TEST_PASSWORD'],
    'HOST': os.environ.get('MYSQL_TEST_HOST', '127.0.0.1'),
    'PORT': os.environ.get('MYSQL_TEST_PORT', '3307'),
    'TEST': {'NAME': 'test_autonexa_ci'},
    'OPTIONS': {'isolation_level': 'read committed'},
}}
