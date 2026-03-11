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


def get_closest_to_date(qs, date):
    greater = qs.filter(date__gte=date).order_by("date").first()
    less = qs.filter(date__lte=date).order_by("-date").first()

    if greater and less:
        return greater if abs(greater.date - date) < abs(less.date - date) else less
    else:
        return greater or less


def extract_datetime_from_filename(filename):
    """
    Extracts datetime from a filename with various patterns.

    Special handling for CHIRPS files where the last number represents dekad:
      - 1 = day 1 of month
      - 2 = day 11 of month
      - 3 = day 21 of month

    Example CHIRPS format: chirps-v2.0.2026.01.2.tif -> 2026-01-11

    Args:
      filename: The name of the file.

    Returns:
      A datetime string (YYYY-MM-DD) if datetime is successfully extracted,
      otherwise None.
    """
    import re
    from datetime import datetime

    # Special case: CHIRPS files with dekad format (YYYY.MM.D where D=1,2,3)
    if "chirps" in filename.lower():
        # Match pattern: YYYY.MM.D (where D is 1, 2, or 3 for dekads)
        match = re.search(r"(\d{4})\.(\d{2})\.([123])", filename)
        if match:
            year = match.group(1)
            month = match.group(2)
            dekad = match.group(3)

            # Map dekad to day: 1->1, 2->11, 3->21
            dekad_to_day = {"1": "01", "2": "11", "3": "21"}
            day = dekad_to_day[dekad]

            datetime_str = f"{year}.{month}.{day}"
            try:
                return datetime.strptime(datetime_str, "%Y.%m.%d").strftime("%Y-%m-%d")
            except ValueError:
                pass

    # Define potential datetime patterns for other products
    patterns = [
        r"\d{4}\.\d{2}\.\d{2}",  # e.g., 2024.11.11
        r"\d{4}\.\d{2}\.\d{1}",  # e.g., 2024.11.3
        r"\d{4}\.\d{1}\.\d{1}",  # e.g., 2024.9.1
        r"\d{4}\.\d{1}\.\d{2}",  # e.g., 2024.9.11
        r"\d{4}-\d{2}-\d{2}",  # e.g., 2024-08-11
        r"\d{4}\d{3}",  # e.g., 2024330 (assuming YYYYDDD format)
        r"\d{4}.\d{3}",  # e.g., 2024.330 (assuming YYYYDDD format)
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            datetime_str = match.group(0)

            if pattern in [
                r"\d{4}\.\d{2}\.\d{2}",
                r"\d{4}\.\d{2}\.\d{1}",
                r"\d{4}\.\d{1}\.\d{1}",
                r"\d{4}\.\d{1}\.\d{2}",
            ]:
                datetime_format = "%Y.%m.%d"
            elif pattern == r"\d{4}-\d{2}-\d{2}":
                datetime_format = "%Y-%m-%d"
            elif pattern == r"\d{4}\d{3}":
                datetime_format = "%Y%j"  # %j for day of the year
            elif pattern == r"\d{4}.\d{3}":
                datetime_format = "%Y.%j"  # %j for day of the year

            try:
                return datetime.strptime(datetime_str, datetime_format).strftime(
                    "%Y-%m-%d"
                )
            except ValueError:
                continue  # Try the next pattern

    return None


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
    """
    There is a bug when using python version 3.9, 3.10 and Django version 4.2 when initiating a sqlite db with spatialite.
    More info here: https://code.djangoproject.com/ticket/32935
    """
    import django

    django.db.connection.cursor().execute("SELECT InitSpatialMetaData(1);")
