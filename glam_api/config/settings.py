"""
Base Django settings for glam_api.

"""

import os
from pathlib import Path

from .utils import get_env_variable

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_variable("GLAM_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_variable("GLAM_DEBUG")

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "modeltranslation",  # Model translations
    "django.contrib.admin",  # Core Django Apps
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",  # GeoDjango
    "django_admin_env_notice",  # Admin evironment notice
    "django_extensions",  # Additional django tools
    "rest_pandas",  # Pandas views integration
    "rest_framework",  # Django REST Framework
    "django_filters",
    "drf_yasg",
    "corsheaders",  # django-cors-headers
    "storages",  # django-storages
    "django_q",  # django-q
    "glam",  # GLAM API
]

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]
    """
    DEBUG TOOLBAR
    """
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: (
            False
            if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
            else True
        ),
    }


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # django-cors-headers
    "debug_toolbar.middleware.DebugToolbarMiddleware",  # django debug toolbar
    "django.middleware.security.SecurityMiddleware",  # django middleware
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATE_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django_admin_env_notice.context_processors.from_settings",  # django_admin_env_notice
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


"""
DATABASE SETTINGS
"""

DATABASES = {
    # Configure database connection in local settings file
}

# Q Cluster Settings

Q_CLUSTER = {
    "timeout": 60,  # default setting to supress misconfiguration warning
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Django Model Translations


def gettext(s):
    return s


LANGUAGES = (
    ("en", gettext("English")),
    ("es", gettext("Spanish")),
    ("pt", gettext("Portuguese")),
)

MODELTRANSLATION_DEFAULT_LANGUAGE = "en"


"""
Storage settings
"""

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Local files
LOCAL_ROOT = os.path.join(BASE_DIR, "local_files")

PRODUCT_DATASET_LOCAL_PATH = os.path.join(LOCAL_ROOT, "product_datasets")

MASK_DATASET_LOCAL_PATH = os.path.join(LOCAL_ROOT, "mask_datasets")

ANOMALY_BASELINE_LOCAL_PATH = os.path.join(LOCAL_ROOT, "baseline_datasets")

IMAGE_EXPORT_LOCAL_PATH = os.path.join(LOCAL_ROOT, "exports")

# Cloud storage

# If True, set AWS S3 storage parameters
USE_S3 = True

### AWS S3 Storage Settings ###
if USE_S3:
    AWS_ACCESS_KEY_ID = get_env_variable("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = get_env_variable("AWS_SECRET_ACCESS_KEY")
    AWS_S3_SESSION_PROFILE = get_env_variable("AWS_S3_SESSION_PROFILE")
    AWS_STORAGE_BUCKET_NAME = get_env_variable("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
else:
    FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

STORAGES = {
    "default": {
        "BACKEND": FILE_STORAGE,
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

"""
Compute Settings - for reading rasters with multiprocessing.
"""

# Set number of processes to 1 by default
N_PROCESSES = 1

BLOCK_SCALE_FACTOR = 4

DEFAULT_BLOCK_SIZE = 256


"""
Tile Server Settings
"""
DEFAULT_TILE_SIZE: int = 512

"""
Other GLAM settings
"""

# Add/remove admin site availability based on deployment.
ADMIN_SITE = True
ADMIN_SITE_NAME = "admin"

LOG_LEVELS = {
    "CRITICAL": 50,
    "ERROR": 40,
    "WARNING": 30,
    "INFO": 20,
    "DEBUG": 10,
    "NOTSET": 0,
}

LOG_LEVEL = "INFO"

"""
DEBUG TOOLBAR
"""
INTERNAL_IPS = [
    "127.0.0.1",
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
