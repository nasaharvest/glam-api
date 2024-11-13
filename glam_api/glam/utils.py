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


def prepare_db():
    import django

    django.db.connection.cursor().execute("SELECT InitSpatialMetaData(1);")
