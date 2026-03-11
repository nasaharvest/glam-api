"""
glam recurring tasks

"""

import os
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

    # Check if directory exists, if not create it
    if not os.path.exists(directory):
        os.makedirs(directory)
        return

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
        try:
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
                start_date = latest.date + timedelta(
                    days=valid_product.composite_period
                )
            else:
                start_date = latest.date + timedelta(days=1)

            end_date = latest.date + timedelta(days=30)

            if not os.path.exists(settings.PRODUCT_DATASET_LOCAL_PATH):
                os.makedirs(settings.PRODUCT_DATASET_LOCAL_PATH)

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
        except Exception as e:
            logging.error(f"Failed to download {product_id}: {e}")

    logging.info(f"Total downloads: {len(downloads)}")
    logging.info(f"{downloads}")
    return downloads


def download_new_by_product(product_id):

    try:
        product = Product.objects.get(product_id=product_id)

        downloads = []

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

        if not os.path.exists(settings.PRODUCT_DATASET_LOCAL_PATH):
            os.makedirs(settings.PRODUCT_DATASET_LOCAL_PATH)

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
    except Exception as e:
        logging.error(f"Failed to download {product_id}: {e}")

    return downloads


def find_and_download_missing():
    """
    Find and download missing datasets for all products.

    Analyzes the date range of existing datasets and identifies gaps
    based on the product's composite period or expected dekad schedule.
    """
    products = Product.objects.all().order_by("product_id")

    for product in tqdm.tqdm(products):
        find_and_download_missing_by_product(product.product_id)


def find_and_download_missing_by_product(product_id):
    """
    Find and download missing datasets for a specific product.

    For CHIRPS: expects 3 datasets per month (dekads 1, 11, 21)
    For composite products: generates expected dates based on composite_period
    For daily products: generates all dates in range
    """
    from datetime import datetime as dt

    try:
        product = Product.objects.get(product_id=product_id)

        # Get all existing dates for this product
        existing_datasets = ProductRaster.objects.filter(product=product).order_by(
            "date"
        )

        if not existing_datasets.exists():
            logging.warning(
                f"No datasets found for {product_id}. Skipping gap analysis."
            )
            return

        existing_dates = set(existing_datasets.values_list("date", flat=True))
        min_date = existing_datasets.first().date
        max_date = existing_datasets.last().date

        logging.info(f"\n{product_id}: Analyzing date range {min_date} to {max_date}")
        logging.info(f"{product_id}: Found {len(existing_dates)} existing datasets")

        # Generate expected dates based on product type
        if product_id == "chirps-precip":
            # CHIRPS has 3 datasets per month at days 1, 11, 21
            expected_dates = _generate_chirps_expected_dates(min_date, max_date)
        else:
            # For other products, use composite period
            if product.composite and product.composite_period:
                expected_dates = _generate_composite_expected_dates(
                    min_date, max_date, product.composite_period
                )
            else:
                # Daily data
                from datetime import date

                expected_dates = set()
                current = min_date
                while current <= max_date:
                    expected_dates.add(current)
                    current += timedelta(days=1)

        # Find missing dates
        missing_dates = sorted(expected_dates - existing_dates)

        if not missing_dates:
            logging.info(f"{product_id}: No missing datasets found")
            return

        logging.info(f"{product_id}: Found {len(missing_dates)} missing datasets")
        logging.info(f"{product_id}: Missing dates: {missing_dates}")

        # Download missing datasets
        _download_specific_dates(product_id, missing_dates)

    except Product.DoesNotExist:
        logging.error(f"Product not found: {product_id}")
    except Exception as e:
        logging.error(f"Failed to find/download missing datasets for {product_id}: {e}")


def _generate_chirps_expected_dates(start_date, end_date):
    """Generate expected CHIRPS dates (dekad 1, 11, 21 of each month)"""
    from datetime import date

    expected = set()
    year, month = start_date.year, start_date.month

    while date(year, month, 1) <= end_date:
        # Dekad 1 (1st)
        d1 = date(year, month, 1)
        if d1 >= start_date and d1 <= end_date:
            expected.add(d1)

        # Dekad 2 (11th)
        d2 = date(year, month, 11)
        if d2 >= start_date and d2 <= end_date:
            expected.add(d2)

        # Dekad 3 (21st)
        d3 = date(year, month, 21)
        if d3 >= start_date and d3 <= end_date:
            expected.add(d3)

        # Move to next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return expected


def _generate_composite_expected_dates(start_date, end_date, composite_period):
    """Generate expected dates based on composite period"""
    expected = set()
    current = start_date

    while current <= end_date:
        expected.add(current)
        current += timedelta(days=composite_period)

    return expected


def _download_specific_dates(product_id, dates):
    """Download data for specific dates"""

    vi = None
    parts = product_id.split("-")

    try:
        if parts[-1] in ["ndvi", "ndwi"]:
            vi = parts[-1].upper()
            downloader = Downloader(parts[0].upper())
        elif parts[-1] == "swi":
            downloader = Downloader(parts[-1])
        elif parts[-1] == "precip":
            downloader = Downloader(parts[0])
        elif parts[-1] == "esi":
            downloader = Downloader(f"{parts[-1]}/{parts[-2].upper()}")
        else:
            logging.warning(f"Unknown product type: {product_id}")
            return

        if not os.path.exists(settings.PRODUCT_DATASET_LOCAL_PATH):
            os.makedirs(settings.PRODUCT_DATASET_LOCAL_PATH)

        successful_downloads = 0
        failed_downloads = 0

        for date_obj in tqdm.tqdm(dates, desc=f"Downloading {product_id}"):
            try:
                # Download a small range around each missing date to catch it
                start = (date_obj - timedelta(days=1)).isoformat()
                end = (date_obj + timedelta(days=1)).isoformat()

                if vi:
                    downloader.download_vi_composites(
                        start, end, settings.PRODUCT_DATASET_LOCAL_PATH, vi=vi
                    )
                else:
                    downloader.download_composites(
                        start, end, settings.PRODUCT_DATASET_LOCAL_PATH
                    )

                successful_downloads += 1
                logging.info(f"  Downloaded {product_id} for {date_obj}")
            except Exception as e:
                failed_downloads += 1
                logging.warning(
                    f"  Failed to download {product_id} for {date_obj}: {e}"
                )

        logging.info(
            f"{product_id}: Downloaded {successful_downloads}/{len(dates)} missing datasets "
            f"({failed_downloads} failed)"
        )

    except Exception as e:
        logging.error(f"Failed to initialize downloader for {product_id}: {e}")
