"""
glam app specific utilities

"""

from typing import Sequence, Tuple, TypeVar, Union
from typing import BinaryIO

import numpy as np


Number = TypeVar("Number", int, float)
RGBA = Tuple[Number, Number, Number, Number]
Palette = Sequence[RGBA]
Array = TypeVar("Array", np.ndarray, np.ma.MaskedArray)


def contrast_stretch(
    data: Array,
    in_range: Sequence[Number],
    out_range: Sequence[Number],
    clip: bool = True,
) -> Array:
    """Normalize input array from in_range to out_range"""
    lower_bound_in, upper_bound_in = in_range
    lower_bound_out, upper_bound_out = out_range

    out_data = data.astype("float64", copy=True)
    out_data -= lower_bound_in
    norm = upper_bound_in - lower_bound_in
    if abs(norm) > 1e-8:  # prevent division by 0
        out_data *= (upper_bound_out - lower_bound_out) / norm
    out_data += lower_bound_out

    if clip:
        np.clip(out_data, *out_range, out=out_data)

    return out_data


def to_uint8(data: Array, lower_bound: Number, upper_bound: Number) -> Array:
    """
    Re-scale an array to [1, 255] and cast to uint8
    (0 is used for transparency)
    """
    rescaled = contrast_stretch(data, (lower_bound, upper_bound), (1, 255), clip=True)
    return rescaled.astype(np.uint8)


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

    Args:
      filename: The name of the file.

    Returns:
      A datetime object if datetime is successfully extracted,
      otherwise None.
    """
    import re
    from datetime import datetime

    # Define potential datetime patterns
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


def get_product_id_from_filename(filename):
    """
    Matches a filename to its corresponding ID from a given list.

    Args:
      filename: The name of the file.

    Returns:
      The matching ID if found, otherwise None.
    """

    if "chirps" in filename:
        return "chirps-precip"
    elif "swi" in filename:
        return "copernicus-swi"
    elif "DFPPM_4WK" in filename:
        return "servir-4wk-esi"
    elif "DFPPM_12WK" in filename:
        return "servir-12wk-esi"
    elif "VNP09H1.ndvi" in filename:
        return "vnp09h1-ndvi"
    elif "MOD09Q1.ndvi" in filename:
        return "mod09q1-ndvi"
    elif "MYD09Q1.ndvi" in filename:
        return "myd09q1-ndvi"
    elif "MOD13Q1.ndvi" in filename:
        return "mod13q1-ndvi"
    elif "MYD13Q1.ndvi" in filename:
        return "myd13q1-ndvi"
    elif "MOD09A1.ndwi" in filename:
        return "mod09a1-ndwi"
    else:
        return None


def prepare_db():
    """
    There is a bug when using python version 3.9, 3.10 and Django version 4.2 when initiating a sqlite db with spatialite.
    More info here: https://code.djangoproject.com/ticket/32935
    """
    import django

    django.db.connection.cursor().execute("SELECT InitSpatialMetaData(1);")
