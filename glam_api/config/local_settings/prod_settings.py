"""
Sample Production Settings
"""

from ..settings import *

DATABASES = {
    ### postgresql/postgis configuration
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": get_env_variable("GLAM_DB_NAME"),
        "USER": get_env_variable("GLAM_DB_USER"),
        "PASSWORD": get_env_variable("GLAM_DB_PASSWORD"),
        "HOST": get_env_variable("GLAM_DB_HOST"),
        "PORT": 5432,
    },
}

# Cloud storage

# If True, set AWS S3 storage parameters
USE_S3 = True

### AWS S3 Storage Settings ###
if USE_S3:

    AWS_ACCESS_KEY_ID = get_env_variable("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = get_env_variable("AWS_SECRET_ACCESS_KEY")

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
