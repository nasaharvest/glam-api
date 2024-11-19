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


def prepare_spatialite_db():
    # https://code.djangoproject.com/ticket/32935
    connection.cursor().execute("SELECT InitSpatialMetaData(1);")
