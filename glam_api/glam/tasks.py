"""
glam recurring tasks

"""

import logging
import tqdm

from datetime import timedelta

from django.conf import settings

from glam_processing.download import Downloader

from .models import Product, ProductRaster

logging.basicConfig(
    format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level=logging.INFO
)


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
    products = Product.objects.all().order_by("product_id")

    downloads = []

    for product in tqdm.tqdm(products):
        product_id = product.product_id
        vi = None

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
            product = Downloader(f"{parts[-1]}/{parts[-2].upper()}")

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
