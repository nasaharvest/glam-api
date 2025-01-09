from decimal import Decimal

import numpy as np

import rasterio
from rio_tiler.io import COGReader

from rest_framework import viewsets
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.shortcuts import get_object_or_404
from django.conf import settings

from ..models import (
    Product,
    ProductRaster,
    AnomalyBaselineRaster,
    CropMask,
    CropmaskRaster,
)
from ..serializers import PointValueSerializer, PointResponseSerializer
from ..utils import get_closest_to_date


class PointValue(viewsets.ViewSet):

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
        description="Date value to identify dataset. ISO-8601 format. \
            \n Example: '2002-04-01'",
        required=True,
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    )

    lon_param = openapi.Parameter(
        "lon",
        openapi.IN_PATH,
        description="Longitude (x) in Decimal Degrees",
        type=openapi.TYPE_NUMBER,
        format=openapi.FORMAT_FLOAT,
    )

    lat_param = openapi.Parameter(
        "lat",
        openapi.IN_PATH,
        description="Latitude (y) in Decimal Degrees",
        type=openapi.TYPE_NUMBER,
        format=openapi.FORMAT_FLOAT,
    )

    cropmask_param = openapi.Parameter(
        "cropmask_id",
        openapi.IN_QUERY,
        description="A unique character ID to identify Crop Mask records.",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_SLUG,
        enum=AVAILABLE_CROPMASKS if len(AVAILABLE_CROPMASKS) > 0 else None,
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

    resp_200 = openapi.Response(
        description="Point response",
        schema=PointResponseSerializer,
        examples={"application/json": {"value": 69.420}},
    )

    @swagger_auto_schema(
        manual_parameters=[
            product_param,
            date_param,
            lon_param,
            lat_param,
            cropmask_param,
            anomaly_param,
            anomaly_type_param,
            diff_year_param,
        ],
        operation_id="get point value",
        responses={200: resp_200},
    )
    def retrieve(
        self,
        request,
        product_id: str = None,
        date: str = None,
        lat: float = None,
        lon: float = None,
        cropmask_id: str = None,
        anomaly: str = None,
        anomaly_type: str = None,
    ):
        """
        Return pixel value for specified coordinates and dataset parameters.
        """

        product_queryset = ProductRaster.objects.filter(product__product_id=product_id)
        product_dataset = get_object_or_404(product_queryset, date=date)

        params = PointValueSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        anomaly = data.get("anomaly", None)
        anomaly_type = data.get("anomaly_type", None)
        diff_year = data.get("diff_year", None)
        cropmask = data.get("cropmask_id", None)
        if cropmask == "no-mask":
            cropmask = None

        if not settings.USE_S3:
            path = product_dataset.file_object.path
        if settings.USE_S3:
            path = f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{product_dataset.file_object.name}"

        dataset_value = None

        with rasterio.Env(**settings.GDAL_CONFIG_OPTIONS) as env:

            if cropmask:
                mask_queryset = CropmaskRaster.objects.all()
                mask_dataset = get_object_or_404(
                    mask_queryset,
                    product__product_id=product_id,
                    crop_mask__cropmask_id=cropmask,
                )

                if not settings.USE_S3:
                    mask_path = mask_dataset.file_object.path
                if settings.USE_S3:
                    mask_path = f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{mask_dataset.file_object.name}"

                with COGReader(mask_path) as src:
                    mask_data = src.point(lon, lat)

            with COGReader(path) as src:
                data = src.point(lon, lat)
                if data[0] == src.nodata:
                    dataset_value = None
                    result = {"value": "No Data"}
                    return Response(result)
                else:
                    if cropmask:
                        data = mask_data[0] * data[0]
                    else:
                        data = data[0]
                    dataset_value = data

            if anomaly_type:
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
                    if product_id == "swi":
                        swi_baselines = np.arange(1, 366, 5)
                        idx = (np.abs(swi_baselines - doy)).argmin()
                        doy = swi_baselines[idx]
                    if product_id == "chirps":
                        doy = int(str(date.month) + f"{date.day:02d}")
                    anomaly_queryset = AnomalyBaselineRaster.objects.all()
                    anomaly_dataset = get_object_or_404(
                        anomaly_queryset,
                        product__product_id=product_id,
                        day_of_year=doy,
                        baseline_length=anomaly,
                        baseline_type=anom_type,
                    )

                if not settings.USE_S3:
                    baseline_path = anomaly_dataset.file_object.path
                if settings.USE_S3:
                    baseline_path = f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{anomaly_dataset.file_object.name}"

                with COGReader(baseline_path) as baseline_img:
                    baseline_data = baseline_img.point(lon, lat)

                    if baseline_data[0] == baseline_img.nodata:
                        result = {"value": "No Data"}
                    else:
                        if cropmask:
                            baseline_value = mask_data[0] * baseline_data[0]
                        else:
                            baseline_value = baseline_data[0]
                        diff = dataset_value - baseline_value
                        result = {
                            "value": float(
                                Decimal(str(diff))
                                * Decimal(str(product_dataset.product.variable.scale))
                            )
                        }

                return Response(result)

            else:
                if dataset_value:
                    result = {
                        "value": float(
                            Decimal(str(dataset_value))
                            * Decimal(str(product_dataset.product.variable.scale))
                        )
                    }
                else:
                    result = {"value": "No Data"}

                return Response(result)
