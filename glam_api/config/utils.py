"""
glam_api project-wide utilities

"""

import os

from django.db import connection

from django.core.exceptions import ImproperlyConfigured
from django.utils.text import slugify


def get_env_variable(var_name):
    """
    Get the environment variable or return exception.
    """

    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the {} environment variable".format(var_name)
        raise ImproperlyConfigured(error_msg)


def generate_unique_slug(instance, slug_field):
    name = instance.name.replace(".", "-")
    base_slug = slugify(name)
    slug = base_slug
    num = 1

    while type(instance).objects.filter(**{f"{slug_field}": f"{slug}"}).exists():
        slug = f"{base_slug}-{num}"
        num += 1

    unique_slug = slug
    return unique_slug


def create_aws_session_env_file(serial_number: str, token: str):
    import boto3
    from django.conf import settings

    client = boto3.client("sts")
    response = client.get_session_token(SerialNumber=serial_number, TokenCode=token)
    credentials = response.get("Credentials")
    access_key_id = credentials.get("AccessKeyId")
    secret_access_key = credentials.get("SecretAccessKey")
    session_token = credentials.get("SessionToken")

    env_file = settings.BASE_DIR / "config" / "aws.env"

    with open(env_file, "w") as f:
        f.write(f"export AWS_ACCESS_KEY_ID={access_key_id}\n")
        f.write(f"export AWS_SECRET_ACCESS_KEY={secret_access_key}\n")
        f.write(f"export AWS_SESSION_TOKEN={session_token}\n")


def prepare_spatialite_db():
    # https://code.djangoproject.com/ticket/32935
    connection.cursor().execute("SELECT InitSpatialMetaData(1);")
