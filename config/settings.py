"""Django settings for Intern Accra.

Secrets and host names come from environment variables, so the same code runs on
your laptop (defaults below) and on a live server (set the variables in the README).
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_list(name, default=''):
    return [x.strip() for x in os.environ.get(name, default).split(',') if x.strip()]


SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-only-key-change-me-in-production')
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

if not DEBUG and (SECRET_KEY.startswith('dev-only') or len(SECRET_KEY) < 40):
    raise RuntimeError('Set DJANGO_SECRET_KEY to a long random value (40+ characters) before running with DJANGO_DEBUG=0.')
if not DEBUG and '*' in ALLOWED_HOSTS:
    raise RuntimeError('DJANGO_ALLOWED_HOSTS must list your real domain, not *.')

# The admin lives here. Set DJANGO_ADMIN_URL to something only you know, e.g. "desk-7f3k".
ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'manage').strip('/') + '/'

# How many proxies sit in front of the site (PythonAnywhere, Render and similar hosts: 1).
# Use 0 if visitors reach the site directly.
TRUSTED_PROXY_COUNT = int(os.environ.get('DJANGO_TRUSTED_PROXIES', '1'))

INSTALLED_APPS = [
    'listings.adminapp.InternAdminConfig',  # Django admin, using our own admin site
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'listings',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'listings.security.SecurityHeadersMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_PATH', BASE_DIR / 'db.sqlite3'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Africa/Accra'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] == 'test'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        # Hashed, compressed files for the live site. Needs `collectstatic` first.
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage' if RUNNING_TESTS
        else 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Admin login lockout: 5 failures per IP + username, or 25 per IP, within 15 minutes.
LOGIN_THROTTLE_LIMIT = 5
LOGIN_THROTTLE_IP_LIMIT = 25
LOGIN_THROTTLE_WINDOW = 15 * 60

# Failed-login counts are kept here. A file cache is shared by all server processes on one machine.
CACHES = {
    'default': (
        {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'} if RUNNING_TESTS else
        {'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
         'LOCATION': os.environ.get('DJANGO_CACHE_DIR', str(BASE_DIR / '.cache'))}
    )
}

# Admin sessions end after 8 hours.
SESSION_COOKIE_AGE = 60 * 60 * 8

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Shown in the site footer so companies can reach you. Digits only, e.g. 233244000000.
CONTACT_WHATSAPP = os.environ.get('CONTACT_WHATSAPP', '')
CONTACT_EMAIL = os.environ.get('CONTACT_EMAIL', '')

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SSL_REDIRECT', '1') == '1'
    # HSTS tells browsers to use HTTPS only. It starts at 1 hour so a mistake is easy to undo.
    # Once HTTPS works everywhere, set DJANGO_HSTS_SECONDS=31536000 (one year).
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '3600'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('DJANGO_HSTS_SUBDOMAINS', '0') == '1'
    SECURE_HSTS_PRELOAD = False
    SILENCED_SYSTEM_CHECKS = ['security.W021']  # preload is a permanent browser-list commitment; left off on purpose
