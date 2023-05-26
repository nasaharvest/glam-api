import os
import logging
import datetime
import tqdm

from django.conf import settings

from ..models import Product, ProductRaster
from ..utils.downloads import GlamDownloader
from ..utils.daac import NASA_PRODUCTS
from ..utils.ingest import add_product_rasters

logging.basicConfig(
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level=settings.LOG_LEVELS[settings.LOG_LEVEL],
)
log = logging.getLogger(__name__)


def daily_download(product_id):
    g = GlamDownloader(product_id)

    if product_id == "mod09a1":
        glam_id = "mod09a1-ndwi"
        vi = "NDWI"
    elif product_id.upper() in NASA_PRODUCTS:
        glam_id = product_id + "-ndvi"
        vi = "NDVI"
    else:
        glam_id = product_id
        vi = None

    rasters = ProductRaster.objects.filter(product__product_id=glam_id).order_by(
        "-date"
    )
    latest = rasters.first().date
    latest = latest + datetime.timedelta(days=1)
    out_dir = os.path.join(settings.PRODUCT_DATASET_LOCAL_PATH, glam_id)
    g.download_available_from_range(
        start_date=latest.isoformat(), end_date=None, out_dir=out_dir, vi=vi
    )


def daily_ingest(product_id):
    if product_id == "mod09a1":
        glam_id = "mod09a1-ndwi"
        vi = "ndwi"
    elif product_id.upper() in NASA_PRODUCTS:
        glam_id = product_id + "-ndvi"
        vi = "ndvi"
    else:
        glam_id = product_id
        vi = None

    # temporary file renaming for legacy glam
    if vi:
        directory = os.path.join(settings.PRODUCT_DATASET_LOCAL_PATH, glam_id)
        files = os.listdir(directory)
        for file in files:
            parts = file.split(".")
            if parts[-1] == "tif":
                if parts[1] == vi:
                    print(parts)
                    parts.remove(vi)
                    sep = "."
                    new_name = sep.join(parts)
                    src = os.path.join(directory, file)
                    dst = os.path.join(directory, new_name)
                    os.rename(src, dst)

    add_product_rasters(glam_id)


def update_chirps_prelim():
    g = GlamDownloader("chirps-precip")
    chirps_prelim = ProductRaster.objects.filter(
        product__product_id="chirps-precip", prelim=True
    )
    for ds in tqdm.tqdm(chirps_prelim):
        avail = g.available_for_download(ds.date.isoformat(), prelim=False)

        # If non-preliminary data available, remove prelim dataset and add regular.
        if avail:
            log.info(
                f"New file available for {ds.date.isoformat()}, deleting prelim entry."
            )
            to_delete = chirps_prelim.get(date=ds.date)
            # Delete file from S3.
            os.remove(to_delete.local_path)
            to_delete.file_object.delete()
            # Delete database record.
            to_delete.delete()
            log.info("Downloading new file.")
            out_dir = os.path.join(settings.PRODUCT_DATASET_LOCAL_PATH, "chirps-precip")
            g.download_single_date(date=ds.date.isoformat(), out_dir=out_dir)

    log.info("Ingesting new files.")
    add_product_rasters("chirps-precip")
