from django.conf import settings

from storages.backends.s3boto3 import S3Boto3Storage


class S3MediaStorage(S3Boto3Storage):
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = True


class PrivateMediaStorage(S3Boto3Storage):
    location = 'private'
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False


class RasterStorage(S3Boto3Storage):
    # https://github.com/jschneier/django-storages/issues/606
    # "The issue appears to be the new behaviour of django-storages to
    # automatically pull the AWS security token from environment variables.
    # AWS Lambda provides AWS_SESSION_TOKEN and AWS_SECURITY_TOKEN as
    # environment variables,
    # taken from the execution role for Lambda which may not be the same
    # credentials required by django-storages for S3 access"

    # Overriding _get_security_token to prevent duplicate security tokens
    if settings.USE_S3_RASTERS:
        def _get_security_token(self):
            return None

    location = ''
    default_acl = 'private'
    file_overwrite = True
    custom_domain = False


class VectorStorage(S3Boto3Storage):
    # https://github.com/jschneier/django-storages/issues/606
    # "The issue appears to be the new behaviour of django-storages to
    # automatically pull the AWS security token from environment variables.
    # AWS Lambda provides AWS_SESSION_TOKEN and AWS_SECURITY_TOKEN as
    # environment variables,
    # taken from the execution role for Lambda which may not be the same
    # credentials required by django-storages for S3 access"

    # Overriding _get_security_token to prevent duplicate security tokens
    if settings.USE_S3_RASTERS:
        def _get_security_token(self):
            return None

    location = ''
    default_acl = 'private'
    file_overwrite = True
    custom_domain = False


class ColormapStorage(S3Boto3Storage):
    # https://github.com/jschneier/django-storages/issues/606
    # "The issue appears to be the new behaviour of django-storages to
    # automatically pull the AWS security token from environment variables.
    # AWS Lambda provides AWS_SESSION_TOKEN and AWS_SECURITY_TOKEN as
    # environment variables,
    # taken from the execution role for Lambda which may not be the same
    # credentials required by django-storages for S3 access"

    # Overriding _get_security_token to prevent duplicate security tokens
    if settings.USE_S3_RASTERS:
        def _get_security_token(self):
            return None

    location = ''
    default_acl = 'private'
    file_overwrite = True
    custom_domain = False


class PublicStorage(S3Boto3Storage):
    location = ''
    default_acl = 'public-read'
    file_overwrite = True
