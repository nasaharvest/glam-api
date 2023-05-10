import os
import datetime

from django.conf import settings

from ..models import Product, ProductRaster
from ..utils.downloads import GlamDownloader
from ..utils.daac import NASA_PRODUCTS
from ..utils.ingest import add_product_rasters

def daily_download(product_id):
    g = GlamDownloader(product_id)

    if product_id == 'mod09a1':
        glam_id = 'mod09a1-ndwi'
        vi = "NDWI"
    elif product_id.upper() in NASA_PRODUCTS:
        glam_id = product_id+'-ndvi'
        vi = "NDVI"
    else:
        glam_id = product_id
        vi = None

    rasters = ProductRaster.objects.filter(product__product_id=glam_id).order_by('-date')
    latest = rasters.first().date
    latest = latest + datetime.timedelta(days=1)
    out_dir = os.path.join(settings.PRODUCT_DATASET_LOCAL_PATH, glam_id)
    g.download_available_from_range(start_date=latest.isoformat(),end_date=None, out_dir=out_dir, vi=vi)


def daily_ingest(product_id):
    add_product_rasters(product_id)
