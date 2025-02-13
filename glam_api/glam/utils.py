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


def upload_files_from_directory(directory, bucket, prefix=""):
    """Upload all files from a directory to a nested S3 location

    Args:
        directory (str): Directory containing files to upload
        bucket (str): Bucket to upload to
        prefix (str): Optional prefix for the S3 objects (e.g., "folder1/folder2/")
    """
    import boto3
    from botocore.exceptions import ClientError
    import os
    import tqdm

    # Create S3 client
    s3_client = boto3.client("s3")

    for filename in tqdm.tqdm(os.listdir(directory)):
        file_path = os.path.join(directory, filename)
        object_name = os.path.join(prefix, os.path.basename(file_path))

        try:
            # Check if the object already exists in the bucket
            s3_client.head_object(Bucket=bucket, Key=object_name)
            logging.debug(
                f"Object '{object_name}' already exists in bucket '{bucket}'. Skipping upload."
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # Object does not exist, proceed with upload
                try:
                    response = s3_client.upload_file(file_path, bucket, object_name)
                    logging.info(f"Uploaded '{file_path}' to '{bucket}/{object_name}'")
                except ClientError as e:
                    logging.info(
                        f"Failed to upload '{file_path}' to '{bucket}/{object_name}'. Error: {e}"
                    )
            else:
                raise e


def download_new():
    products = Product.objects.all()

    downloads = []

    for product in tqdm.tqdm(products):
        product_id = product.product_id

        try:
            valid_product = Product.objects.get(product_id=product_id)
            latest = (
                ProductRaster.objects.filter(product=valid_product)
                .order_by("-date")
                .first()
            )
            logging.info(f"latest date for {product_id}: {latest.date.isoformat()}")

        except Product.DoesNotExist:
            return

        parts = product_id.split("-")
        if parts[-1] in ["ndvi", "ndwi"]:
            vi = parts[-1].upper()
            product = Downloader(parts[0].upper())
        elif parts[-1] == "swi":
            product = Downloader(parts[-1])
        elif parts[-1] == "precip":
            product = Downloader(parts[0])
        elif parts[-1] == "esi":
            product = Downloader(f"{parts[-1]}/{parts[-2]}")

        if valid_product.composite:
            start_date = latest.date + timedelta(days=valid_product.composite_period)
        else:
            start_date = latest.date + timedelta(days=1)

        end_date = latest.date + timedelta(days=30)

        if vi:
            out = product.download_vi_composites(
                start_date.isoformat(),
                end_date.isoformat(),
                settings.PRODUCT_DATASET_LOCAL_PATH,
                vi=vi,
            )
        else:
            out = product.download_composites(
                start_date.isoformat(),
                end_date.isoformat(),
                settings.PRODUCT_DATASET_LOCAL_PATH,
            )

        downloads.append(out)
        logging.info(f"{product_id} files downloaded: {out}")

    logging.info(f"Total downloads: {len(downloads)}")
    logging.info(f"{downloads}")
    return downloads
