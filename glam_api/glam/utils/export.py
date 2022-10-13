import os
import datetime
import math
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.files import File
from numpy import False_

import rasterio
from rasterio.io import MemoryFile
from rasterio.mask import mask
from rasterio import features
from rasterio.rio.overview import get_maximum_overview_level
from rasterio.enums import Resampling

from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles

from shapely.geometry import shape, mapping
from shapely.ops import transform

from affine import Affine

import pyproj
from pyproj import CRS

from ..models import (ProductDataset, ImageExport)


def image_export(export_id, data):

    product_id = data.get('product_id', None)
    date = data.get('date', None)
    geom = data.get('geom', None)
    anomaly = data.get('anomaly', None)
    anomaly_type = data.get('anomaly_type', None)
    diff_year = data.get('diff_year', None)
    cropmask = data.get('cropmask_id', None)
    if cropmask == 'none':
        cropmask = None

    product_queryset = ProductDataset.objects.filter(
        product__product_id=product_id
    )
    product_dataset = get_object_or_404(
        product_queryset,
        date=date
    )

    if not settings.USE_S3_RASTERS:
        path = product_dataset.file_object.path
    if settings.USE_S3_RASTERS:
        path = product_dataset.file_object.url

    # if feature collection get first feature
    if geom['type'] == 'FeatureCollection':
        geom = geom['features'][0]

    geometry = geom['geometry']
    geom = shape(geometry)

    with rasterio.open(path) as src:
        product_crs = src.crs
        wgs84 = pyproj.CRS('EPSG:4326')
        project = pyproj.Transformer.from_crs(
            wgs84, product_crs, always_xy=True).transform
        new_geom = transform(project, geom)
        no_data = src.nodata

        out_image, out_transform = mask(src, [mapping(new_geom)], crop=True)
        out_meta = src.meta
        out_meta.update({"driver": "GTiff",
                         "height": out_image.shape[1],
                         "width": out_image.shape[2],
                         "transform": out_transform})

    cog_options = cog_profiles.get("deflate")
    out_meta.update(cog_options)
    filename = f'{settings.IMAGE_EXPORT_LOCAL_PATH}/{export_id}.tif'

    with MemoryFile() as memfile:
        with memfile.open(**out_meta) as mem:
            mem.write(out_image)
            cog_translate(
                mem,
                filename,
                out_meta,
                in_memory=False,
                quiet=True,
            )

    # with rasterio.open(filename, 'w', **out_meta) as dst:
    #     dst.write(out_image)

    return export_id


def upload_export(task):
    export_id = task.result
    export = ImageExport.objects.get(id=export_id)

    filename = f'{settings.IMAGE_EXPORT_LOCAL_PATH}/{export_id}.tif'
    print(filename)
    # add file to export object & upload to s3
    with open(filename, 'rb') as f:
        export.file_object = File(f, name=os.path.basename(f.name))
        export.save()
    
    export = ImageExport.objects.get(id=export_id)
    export.completed=datetime.datetime.now()
    export.save()
