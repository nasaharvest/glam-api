"""
glam app specific utilities

"""

import logging
import tqdm

from datetime import datetime, timedelta

from typing import Sequence, Tuple, TypeVar, Union
from typing import BinaryIO

import numpy as np

from django.conf import settings

from glam_processing.download import Downloader

from .models import Product, ProductRaster
from .ingest import add_product_rasters_from_storage

logging.basicConfig(
    format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level=logging.INFO
)

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


def get_product_id_from_filename(filename):
    """
    Matches a filename to its corresponding ID from a given list.

    Args:
      filename: The name of the file.

    Returns:
      The matching ID if found, otherwise None.
    """

    filename = filename.lower()

    if "chirps" in filename:
        return "chirps-precip"
    elif "swi" in filename:
        return "copernicus-swi"
    elif any(text in filename for text in ["dfppm_4wk", "dfppm-4wk"]):
        return "servir-4wk-esi"
    elif any(text in filename for text in ["dfppm_12wk", "dfppm-12wk"]):
        return "servir-12wk-esi"
    elif any(text in filename for text in ["vnp09h1.ndvi", "vnp09h1-ndvi"]):
        return "vnp09h1-ndvi"
    elif any(text in filename for text in ["mod09q1.ndvi", "mod09q1-ndvi"]):
        return "mod09q1-ndvi"
    elif any(text in filename for text in ["myd09q1.ndvi", "myd09q1-ndvi"]):
        return "myd09q1-ndvi"
    elif any(text in filename for text in ["mod13q1.ndvi", "mod13q1-ndvi"]):
        return "mod13q1-ndvi"
    elif any(text in filename for text in ["myd13q1.ndvi", "myd13q1-ndvi"]):
        return "myd13q1-ndvi"
    elif any(text in filename for text in ["mod09a1.ndwi", "mod09a1-ndwi"]):
        return "mod09a1-ndwi"
    else:
        return None
