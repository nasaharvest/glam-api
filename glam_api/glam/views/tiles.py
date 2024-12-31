import datetime
import time
import logging

from typing import Mapping, Union, Tuple, TypeVar
from typing import BinaryIO

import numpy as np
import matplotlib

import rasterio

from rio_tiler.io import COGReader
from rio_tiler.colormap import cmap
from rio_tiler.profiles import img_profiles
from rio_tiler.models import ImageData

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.conf import settings
from django.shortcuts import get_object_or_404

from ..serializers import TilesSerializer
from ..renderers import PNGRenderer

from ..models import (
    Product,
    ProductRaster,
    CropMask,
    CropmaskRaster,
    AnomalyBaselineRaster,
)

from ..utils import get_closest_to_date

logging.basicConfig(
    format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level=logging.DEBUG
)

AVAILABLE_CMAPS = cmap.list()


Number = TypeVar("Number", int, float)
RGBA = Tuple[Number, Number, Number, Number]

AVAILABLE_PRODUCTS = list()
AVAILABLE_CROPMASKS = list()
ANOMALY_LENGTH_CHOICES = list()
ANOMALY_TYPE_CHOICES = list()

try:
    products = Product.objects.all()
    for c in products:
        AVAILABLE_PRODUCTS.append(c.product_id)
except:
    pass

try:
    cropmasks = CropMask.objects.all()
    for c in cropmasks:
        AVAILABLE_CROPMASKS.append(c.cropmask_id)
except:
    pass

try:
    for length in AnomalyBaselineRaster.BASELINE_LENGTH_CHOICES:
        ANOMALY_LENGTH_CHOICES.append(length[0])
    for type in AnomalyBaselineRaster.BASELINE_TYPE_CHOICES:
        ANOMALY_TYPE_CHOICES.append(type[0])
    ANOMALY_TYPE_CHOICES.append("diff")
except:
    pass


class Tiles(viewsets.ViewSet):
    renderer_classes = [PNGRenderer]

    # Manually Defined Parameter Schemas
    product_param = openapi.Parameter(
        "product_id",
        openapi.IN_PATH,
        description="A unique integer value identifying a dataset.",
        required=True,
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_SLUG,
        enum=AVAILABLE_PRODUCTS if len(AVAILABLE_PRODUCTS) > 0 else None,
    )

    date_param = openapi.Parameter(
        "date",
        openapi.IN_PATH,
        description="isodate.",
        required=True,
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    )

    z_param = openapi.Parameter(
        "z",
        openapi.IN_PATH,
        description="Tile Zoom value.",
        required=True,
        type=openapi.TYPE_INTEGER,
    )

    x_param = openapi.Parameter(
        "x",
        openapi.IN_PATH,
        description="Tile X Value.",
        required=True,
        type=openapi.TYPE_INTEGER,
    )

    y_param = openapi.Parameter(
        "y",
        openapi.IN_PATH,
        description="Tile Y Value.",
        required=True,
        type=openapi.TYPE_INTEGER,
    )

    cropmask_param = openapi.Parameter(
        "cropmask_id",
        openapi.IN_QUERY,
        description="A unique character ID to identify Crop Mask records.",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_SLUG,
        enum=AVAILABLE_CROPMASKS if len(AVAILABLE_CROPMASKS) > 0 else None,
    )

    cropmask_threshold_param = openapi.Parameter(
        "cropmask_threshold",
        openapi.IN_QUERY,
        required=False,
        description="A unique character ID to identify Crop Mask records.",
        type=openapi.TYPE_NUMBER,
    )

    anomaly_param = openapi.Parameter(
        "anomaly",
        openapi.IN_QUERY,
        description="String representing anomaly baseline length",
        type=openapi.TYPE_STRING,
        enum=ANOMALY_LENGTH_CHOICES if len(ANOMALY_LENGTH_CHOICES) > 0 else None,
    )

    anomaly_type_param = openapi.Parameter(
        "anomaly_type",
        openapi.IN_QUERY,
        description="String representing anomaly type",
        type=openapi.TYPE_STRING,
        enum=ANOMALY_TYPE_CHOICES if len(ANOMALY_TYPE_CHOICES) > 0 else None,
    )

    diff_year_param = openapi.Parameter(
        "diff_year",
        openapi.IN_QUERY,
        description="Provide year to see difference image from",
        type=openapi.TYPE_INTEGER,
    )

    colormap_param = openapi.Parameter(
        "colormap",
        openapi.IN_QUERY,
        description="String representing colormap to apply to tile.",
        required=False,
        type=openapi.TYPE_STRING,
        enum=AVAILABLE_CMAPS,
    )

    stretch_min_param = openapi.Parameter(
        "stretch_min",
        openapi.IN_QUERY,
        description="Minimum stretch range value.",
        type=openapi.TYPE_NUMBER,
        required=False,
    )

    stretch_max_param = openapi.Parameter(
        "stretch_max",
        openapi.IN_QUERY,
        description="Maximum stretch range value.",
        type=openapi.TYPE_NUMBER,
        required=False,
    )

    tile_size_param = openapi.Parameter(
        "tile_size",
        openapi.IN_QUERY,
        description="Pixel dimensions of the returned PNG image" " as JSON list.",
        type=openapi.TYPE_INTEGER,
        required=False,
    )

    @swagger_auto_schema(
        manual_parameters=[
            product_param,
            date_param,
            z_param,
            x_param,
            y_param,
            cropmask_param,
            cropmask_threshold_param,
            anomaly_param,
            anomaly_type_param,
            diff_year_param,
            colormap_param,
            stretch_min_param,
            stretch_max_param,
            tile_size_param,
        ],
        operation_id="retrieve tile",
    )
    def retrieve(
        self,
        request,
        product_id: str = None,
        date: str = None,
        z: int = None,
        x: int = None,
        y: int = None,
        cropmask_id: str = None,
        cropmask_threshold: Number = None,
        anomaly: str = None,
        anomaly_type: str = None,
        colormap: Union[str, Mapping[Number, RGBA], None] = None,
        stretch_min: Number = None,
        stretch_max: Number = None,
        tile_size: int = None,
    ) -> BinaryIO:
        """
        Return singleband raster image as PNG \
            for specified zoom and tile coordinates.
        """

        product_queryset = ProductRaster.objects.filter(product__product_id=product_id)
        product_dataset = get_object_or_404(product_queryset, date=date)

        params = TilesSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        anomaly = data.get("anomaly", None)
        anomaly_type = data.get("anomaly_type", None)
        diff_year = data.get("diff_year", None)
        cropmask_id = data.get("cropmask_id", None)
        cropmask_threshold = data.get("cropmask_threshold", None)
        colormap = data.get("colormap", None)
        stretch_min = data.get("stretch_min", None)
        stretch_max = data.get("stretch_max", None)
        tile_size = data.get("tile_size", None)

        if tile_size is None:
            tile_size = settings.DEFAULT_TILE_SIZE

        if product_dataset.product.meta:
            try:
                stretch_range = product_dataset.product.meta["default_stretch"]
            except:
                stretch_range = None
        else:
            stretch_range = None

        if stretch_min is not None and stretch_max is not None:
            stretch_range = [stretch_min, stretch_max]

        with rasterio.Env(**settings.GDAL_CONFIG_OPTIONS) as env:
            for key, value in env.options.items():
                logging.debug(f"GDAL env option: {key}: {value}")

            with COGReader(
                f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{product_dataset.file_object.name}"
            ) as cog:
                img = cog.tile(x, y, z, tilesize=tile_size, reproject_method="bilinear")

            if anomaly or anomaly_type == "diff":
                anom_type = anomaly_type if anomaly_type else "mean"

                if anom_type == "diff":
                    new_year = diff_year
                    new_date = product_dataset.date.replace(year=new_year)
                    anomaly_queryset = ProductRaster.objects.filter(
                        product__product_id=product_id
                    )
                    closest = get_closest_to_date(anomaly_queryset, new_date)

                    try:
                        anomaly_dataset = get_object_or_404(
                            product_queryset, date=new_date
                        )
                    except:
                        anomaly_dataset = closest

                else:
                    doy = product_dataset.date.timetuple().tm_yday

                    if product_id in ["chirps-precip", "copernicus-swi"]:
                        doy = int(str(date.month) + str(date.day).zfill(2))
                    anomaly_queryset = AnomalyBaselineRaster.objects.all()
                    anomaly_dataset = get_object_or_404(
                        anomaly_queryset,
                        product__product_id=product_id,
                        day_of_year=doy,
                        baseline_length=anomaly,
                        baseline_type=anom_type,
                    )

                # if stretch not specified, use standard deviation
                if stretch_min is None and stretch_max is None:
                    try:
                        stretch_range = product_dataset.product.meta["anomaly_stretch"]
                    except:
                        stretch_range = [-100, 100]

                with COGReader(
                    f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{anomaly_dataset.file_object.name}"
                ) as cog:
                    baseline = cog.tile(
                        x, y, z, tilesize=tile_size, reproject_method="bilinear"
                    )

                diff = img.array - baseline.array

                img = ImageData(diff)

            if cropmask_id:
                cropmask = CropMask.objects.get(cropmask_id=cropmask_id)

                with COGReader(
                    f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{cropmask.map_raster.name}"
                ) as cog:
                    cm_img = cog.tile(
                        x, y, z, tilesize=tile_size, reproject_method="bilinear"
                    )

                mask_type = cropmask.mask_type

                crop_mask = cm_img.array.mask
                if mask_type == "percent":
                    if cropmask_threshold:
                        threshold = cropmask_threshold / 100
                    else:
                        threshold = 0.5
                    threshold_mask = cm_img.data < threshold
                    crop_mask = threshold_mask
                    # cm_img.mask[np.where(cm_img.data[0] < threshold)] = 0

                # new_mask = np.minimum(mask, crop_mask)
                img.array = np.ma.masked_array(img.array, mask=crop_mask)

            image_rescale = img.post_process(
                in_range=((stretch_range[0], stretch_range[1]),), out_range=((0, 255),)
            )

            ndvi = matplotlib.colors.LinearSegmentedColormap.from_list(
                "ndvi",
                [
                    "#fffee1",
                    "#ffe1c8",
                    "#f5c98c",
                    "#ffdd55",
                    "#ebbe37",
                    "#faffb4",
                    "#e6fa9b",
                    "#cdff69",
                    "#aff05a",
                    "#a0f5a5",
                    "#82e187",
                    "#78c878",
                    "#9ec66c",
                    "#8caf46",
                    "#46b928",
                    "#329614",
                    "#147850",
                    "#1e5000",
                    "#003200",
                ],
                256,
            )

            if colormap is None:
                # use product's default colormap
                if anomaly or anomaly_type == "diff":
                    if product_dataset.product.meta["anomaly_colormap"]:
                        colormap = product_dataset.product.meta["anomaly_colormap"]
                    else:
                        colormap = None
                else:
                    if product_dataset.product.meta["default_colormap"]:
                        colormap = product_dataset.product.meta["default_colormap"]
                    else:
                        colormap = None

            if colormap == "ndvi":
                x = np.linspace(0, 1, 256)
                cmap_vals = ndvi(x)[:, :]
                cmap_uint8 = (cmap_vals * 255).astype("uint8")
                ndvi_dict = {idx: tuple(value) for idx, value in enumerate(cmap_uint8)}
                new = cmap.register({"ndvi": ndvi_dict})
                cm = new.get("ndvi")
            else:
                cm = cmap.get(colormap)

            tile = image_rescale.render(
                img_format="PNG", **img_profiles.get("png"), colormap=cm, add_mask=True
            )

            return Response(tile)

    @swagger_auto_schema(
        manual_parameters=[
            product_param,
            date_param,
            cropmask_param,
            anomaly_param,
            anomaly_type_param,
            diff_year_param,
            colormap_param,
            stretch_min_param,
            stretch_max_param,
            tile_size_param,
        ],
        operation_id="preview tiles",
    )
    def preview(
        self,
        request,
        product_id: str = None,
        date: str = None,
        cropmask_id: str = None,
        anomaly: str = None,
        anomaly_type: str = None,
        colormap: Union[str, Mapping[Number, RGBA], None] = None,
        stretch_min: Number = None,
        stretch_max: Number = None,
        tile_size: int = None,
    ) -> BinaryIO:
        """
        Return overview of image tiles as PNG. (Zoom 0)
        """
        product_queryset = ProductRaster.objects.filter(product__product_id=product_id)
        product_dataset = get_object_or_404(product_queryset, date=date)
        # tile 0
        x = 0
        y = 0
        z = 0

        params = TilesSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        anomaly = data.get("anomaly", None)
        anomaly_type = data.get("anomaly_type", None)
        diff_year = data.get("diff_year", None)
        cropmask = data.get("cropmask_id", None)
        colormap = data.get("colormap", None)
        stretch_min = data.get("stretch_min", None)
        stretch_max = data.get("stretch_max", None)
        tile_size = data.get("tile_size", None)

        if tile_size is None:
            tile_size = settings.DEFAULT_TILE_SIZE

        if product_dataset.product.meta:
            try:
                stretch_range = product_dataset.product.meta["default_stretch"]
            except:
                stretch_range = None
        else:
            stretch_range = None

        if stretch_min is not None and stretch_max is not None:
            stretch_range = [stretch_min, stretch_max]

        with rasterio.Env(**settings.GDAL_CONFIG_OPTIONS) as env:
            with COGReader(
                f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{product_dataset.file_object.name}"
            ) as cog:
                img = cog.tile(x, y, z, tilesize=tile_size)
                # todo if stretch_range = None get range from image

            if anomaly or anomaly_type == "diff":
                anom_type = anomaly_type if anomaly_type else "mean"

                if anom_type == "diff":
                    new_year = diff_year
                    new_date = product_dataset.date.replace(year=new_year)
                    anomaly_queryset = ProductRaster.objects.filter(
                        product__product_id=product_id
                    )
                    closest = get_closest_to_date(anomaly_queryset, new_date)
                    try:
                        anomaly_dataset = get_object_or_404(
                            product_queryset, date=new_date
                        )
                    except:
                        anomaly_dataset = closest

                else:
                    doy = product_dataset.date.timetuple().tm_yday

                    if product_id in ["chirps-precip", "copernicus-swi"]:
                        doy = int(str(date.month) + str(date.day).zfill(2))
                    anomaly_queryset = AnomalyBaselineRaster.objects.all()
                    anomaly_dataset = get_object_or_404(
                        anomaly_queryset,
                        product__product_id=product_id,
                        day_of_year=doy,
                        baseline_length=anomaly,
                        baseline_type=anom_type,
                    )

                # if stretch not specified, use standard deviation
                if stretch_min is None and stretch_max is None:
                    try:
                        stretch_range = product_dataset.product.meta["anomaly_stretch"]
                    except:
                        stretch_range = [-100, 100]

                with COGReader(
                    f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{anomaly_dataset.file_object.name}"
                ) as cog:
                    baseline = cog.tile(x, y, z, tilesize=tile_size)

                anom = img.as_masked().data - baseline.as_masked().data

                img = ImageData(data=anom, mask=img.mask)

            if cropmask:
                mask_queryset = CropmaskRaster.objects.all()
                mask_dataset = get_object_or_404(
                    mask_queryset,
                    product__product_id=product_id,
                    crop_mask__cropmask_id=cropmask,
                )
                with COGReader(mask_dataset.file_object.url) as cog:
                    cm_img = cog.tile(x, y, z, tilesize=tile_size)

                mask = np.minimum(img.mask, cm_img.mask)
                img = ImageData(data=img.data, mask=mask)

            image_rescale = img.post_process(
                in_range=((stretch_range[0], stretch_range[1]),), out_range=((0, 255),)
            )

            ndvi = matplotlib.colors.LinearSegmentedColormap.from_list(
                "ndvi",
                [
                    "#fffee1",
                    "#ffe1c8",
                    "#f5c98c",
                    "#ffdd55",
                    "#ebbe37",
                    "#faffb4",
                    "#e6fa9b",
                    "#cdff69",
                    "#aff05a",
                    "#a0f5a5",
                    "#82e187",
                    "#78c878",
                    "#9ec66c",
                    "#8caf46",
                    "#46b928",
                    "#329614",
                    "#147850",
                    "#1e5000",
                    "#003200",
                ],
                256,
            )

            if colormap is None:
                # use product's default colormap
                if anomaly or anomaly_type == "diff":
                    if product_dataset.product.meta["anomaly_colormap"]:
                        colormap = product_dataset.product.meta["anomaly_colormap"]
                    else:
                        colormap = None
                else:

                    if product_dataset.product.meta["default_colormap"]:
                        colormap = product_dataset.product.meta["default_colormap"]
                    else:
                        colormap = None

            if colormap == "ndvi":
                x = np.linspace(0, 1, 256)
                cmap_vals = ndvi(x)[:, :]
                cmap_uint8 = (cmap_vals * 255).astype("uint8")
                ndvi_dict = {idx: tuple(value) for idx, value in enumerate(cmap_uint8)}
                new = cmap.register({"ndvi": ndvi_dict})
                cm = new.get("ndvi")
            else:
                cm = cmap.get(colormap)

            tile = image_rescale.render(
                img_format="PNG", **img_profiles.get("png"), colormap=cm, add_mask=True
            )
            return Response(tile)
