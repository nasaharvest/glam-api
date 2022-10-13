"""
Base Django settings for glam_api.

"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Function to retreive environment variables using os module.


def get_env_variable(var_name):
    """ Get the environment variable or return exception. """
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the {} environment variable".format(var_name)
        raise ImproperlyConfigured(error_msg)


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_variable("GLAM_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    # Model translations
    'modeltranslation',

    # Core Django Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # GeoDjango
    'django.contrib.gis',

    # Admin evironment notice
    'django_admin_env_notice',

    # Additional django tools
    'django_extensions',

    # Pandas views integration
    'rest_pandas',

    # Django REST Framework
    'rest_framework',
    'django_filters',
    'drf_yasg',

    # django-cors-headers
    'corsheaders',

    # django-storages
    'storages',

    # GLAM API
    'glam'
]

MIDDLEWARE = [
    # django-cors-headers
    'corsheaders.middleware.CorsMiddleware',

    # core django middleware
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # django_admin_env_notice
                'django_admin_env_notice.context_processors.from_settings'
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


"""
DATABASE SETTINGS
"""

DATABASES = {

}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

# Django Model Translations


def gettext(s): return s


LANGUAGES = (
    ('en', gettext('English')),
    ('es', gettext('Spanish')),
    ('pt', gettext('Portuguese')),
)

MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'

# EST Time Zone
TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = True


"""
Storage settings
"""

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Local files
LOCAL_ROOT = os.path.join(BASE_DIR, 'local_files')

PRODUCT_DATASET_LOCAL_PATH = os.path.join(LOCAL_ROOT, 'product_datasets')

MASK_DATASET_LOCAL_PATH = os.path.join(LOCAL_ROOT, 'mask_datasets')

ADMIN_DATASET_LOCAL_PATH = os.path.join(LOCAL_ROOT, 'admin_datasets')

ANOMALY_BASELINE_LOCAL_PATH = os.path.join(LOCAL_ROOT, 'baseline_datasets')

IMAGE_EXPORT_LOCAL_PATH = os.path.join(LOCAL_ROOT, 'exports')

# Cloud storage

# Use AWS S3 to store Raster Files
USE_S3_RASTERS = False

# Use AWS S3 to store static assets rather than local storage root
USE_S3_STATIC = False

# If True, set AWS S3 storage parameters
if USE_S3_RASTERS or USE_S3_STATIC:
    USE_S3 = True
else:
    USE_S3 = False

### AWS S3 Storage Settings ###
if USE_S3:
    AWS_ACCESS_KEY_ID = get_env_variable('AWS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = get_env_variable('AWS_KEY')
    AWS_STORAGE_BUCKET_NAME = get_env_variable('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400'
    }
    ### Settings for static files in S3 ###
    if USE_S3_STATIC:
        AWS_DEFAULT_ACL = 'public-read'
        AWS_LOCATION = 'static'
        STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
        STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

        DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'


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

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Add/remove admin site availability based on deployment.
ADMIN_SITE = True
ADMIN_SITE_NAME = 'admin'

LOG_LEVELS = {
    "CRITICAL": 50,
    "ERROR": 40,
    "WARNING": 30,
    "INFO": 20,
    "DEBUG": 10,
    "NOTSET": 0
}

LOG_LEVEL = 'INFO'


"""
DEBUG TOOLBAR
"""
INTERNAL_IPS = [
    '127.0.0.1',
]
