import json
from decimal import Decimal, InvalidOperation

import numpy as np

from rio_tiler.io import COGReader

import rasterio
from rasterio import features

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.shortcuts import get_object_or_404
from django.conf import settings

from ..models import (
    Product,
    ProductRaster,
    CropMask,
    CropmaskRaster,
    BoundaryFeature,
    BoundaryLayer,
    AnomalyBaselineRaster,
    DataSource,
)
from ..serializers import (
    FeatureBodySerializer,
    FeatureResponseSerializer,
    QueryBoundaryFeatureSerializer,
)
from ..utils import get_closest_to_date

AVAILABLE_PRODUCTS = list()
AVAILABLE_CROPMASKS = list()
AVAILABLE_BOUNDARY_LAYERS = list()
ANOMALY_LENGTH_CHOICES = list()
ANOMALY_TYPE_CHOICES = list()

try:
    products = Product.objects.all()
    for p in products:
        AVAILABLE_PRODUCTS.append(p.product_id)
except:
    pass

try:
    cropmasks = CropMask.objects.all()
    for c in cropmasks:
        AVAILABLE_CROPMASKS.append(c.cropmask_id)
except:
    pass

try:
    boundary_layers = BoundaryLayer.objects.all()
    for l in boundary_layers:
        AVAILABLE_BOUNDARY_LAYERS.append(l.layer_id)
except:
    pass

try:
    for length in AnomalyBaselineRaster.BASELINE_LENGTH_CHOICES:
        ANOMALY_LENGTH_CHOICES.append(length[0])
    for t in AnomalyBaselineRaster.BASELINE_TYPE_CHOICES:
        ANOMALY_TYPE_CHOICES.append(t[0])
    ANOMALY_TYPE_CHOICES.append("diff")
except:
    pass


class QueryRasterValue(viewsets.ViewSet):
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

    cropmask_param = openapi.Parameter(
        "cropmask_id",
        openapi.IN_PATH,
        description="A unique character ID to identify Crop Mask records.",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_SLUG,
        enum=AVAILABLE_CROPMASKS if len(AVAILABLE_CROPMASKS) > 0 else None,
    )

    boundary_layer_param = openapi.Parameter(
        "layer_id",
        openapi.IN_PATH,
        description="A unique character ID to identify Boundary Layer records.",
        required=True,
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_SLUG,
        enum=AVAILABLE_BOUNDARY_LAYERS if len(AVAILABLE_BOUNDARY_LAYERS) > 0 else None,
    )

    boundary_feature_param = openapi.Parameter(
        "feature_id",
        openapi.IN_PATH,
        description="Boundary Feature ID.",
        # required=True,
        type=openapi.TYPE_INTEGER,
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
        schema=FeatureResponseSerializer,
        examples={
            "application/json": {
                "min": 45.17399978637695,
                "max": 221.01995849609375,
                "mean": 94.43216405053599,
                "std": 34.10421337679452,
            }
        },
    )

    @swagger_auto_schema(
        manual_parameters=[],
        operation_id="query custom feature",
        request_body=FeatureBodySerializer,
        responses={200: resp_200},
    )
    def query_custom_feature(self, request):
        """
        Return basic raster statistics for specified polygon.
        """

        if request.method == "POST":
            params = FeatureBodySerializer(data=request.data)
            params.is_valid(raise_exception=True)
            data = params.validated_data

            product_id = data.get("product_id", None)
            date = data.get("date", None)
            geom = data.get("geom", None)
            anomaly = data.get("anomaly", None)
            anomaly_type = data.get("anomaly_type", None)
            diff_year = data.get("diff_year", None)
            cropmask = data.get("cropmask_id", None)
            if cropmask == "no-mask":
                cropmask = None

            product_queryset = ProductRaster.objects.filter(
                product__product_id=product_id
            )
            product_dataset = get_object_or_404(product_queryset, date=date)

            if not settings.USE_S3:
                path = product_dataset.file_object.path
            if settings.USE_S3:
                path = f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{product_dataset.file_object.name}"

            if (
                geom["geometry"]["type"] == "Polygon"
                or geom["geometry"]["type"] == "MultiPolygon"
            ):
                try:
                    with COGReader(path) as product_src:
                        feat = product_src.feature(geom, max_size=1024)
                        data = feat.as_masked()

                        mean = float(
                            Decimal(str(data.mean()))
                            * Decimal(str(product_dataset.product.variable.scale))
                        )
                        _min = float(
                            Decimal(str(data.min()))
                            * Decimal(str(product_dataset.product.variable.scale))
                        )
                        _max = float(
                            Decimal(str(data.max()))
                            * Decimal(str(product_dataset.product.variable.scale))
                        )
                        stdev = float(
                            Decimal(str(data.std()))
                            * Decimal(str(product_dataset.product.variable.scale))
                        )

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

                        with COGReader(mask_path) as mask_src:
                            mask_feat = mask_src.feature(geom, max_size=1024)
                            mask_data = mask_feat.as_masked()

                            data = data * mask_data

                            mean = float(
                                Decimal(str(data.mean()))
                                * Decimal(str(product_dataset.product.variable.scale))
                            )
                            _min = float(
                                Decimal(str(data.min()))
                                * Decimal(str(product_dataset.product.variable.scale))
                            )
                            _max = float(
                                Decimal(str(data.max()))
                                * Decimal(str(product_dataset.product.variable.scale))
                            )
                            stdev = float(
                                Decimal(str(data.std()))
                                * Decimal(str(product_dataset.product.variable.scale))
                            )

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

                        with COGReader(baseline_path) as baseline_src:
                            baseline_feat = baseline_src.feature(geom, max_size=1024)
                            baseline_data = baseline_feat.as_masked()

                        if cropmask:
                            # mask baseline data
                            baseline_data = baseline_data * mask_data

                        mean = data.mean() - baseline_data.mean()
                        _min = data.min() - baseline_data.min()
                        _max = data.max() - baseline_data.max()
                        stdev = data.std() - baseline_data.std()

                        mean = float(
                            Decimal(str(mean))
                            * Decimal(str(product_dataset.product.variable.scale))
                        )
                        _min = float(
                            Decimal(str(_min))
                            * Decimal(str(product_dataset.product.variable.scale))
                        )
                        _max = float(
                            Decimal(str(_max))
                            * Decimal(str(product_dataset.product.variable.scale))
                        )
                        stdev = float(
                            Decimal(str(stdev))
                            * Decimal(str(product_dataset.product.variable.scale))
                        )

                    if type(mean) != np.ma.core.MaskedConstant:
                        result = {"min": _min, "max": _max, "mean": mean, "std": stdev}
                    else:
                        result = {"value": "No Data"}
                        return Response(result)
                except InvalidOperation:
                    result = {"value": "No Data"}

                return Response(result)

            else:
                raise APIException(
                    "Geometry must be of type 'Polygon' or 'MultiPolygon"
                )

    @swagger_auto_schema(
        operation_id="query boundary feature",
        manual_parameters=[
            product_param,
            date_param,
            cropmask_param,
            boundary_layer_param,
            boundary_feature_param,
            anomaly_param,
            anomaly_type_param,
            diff_year_param,
        ],
    )
    def query_boundary_feature(
        self,
        request,
        product_id: str = None,
        date: str = None,
        cropmask_id: str = None,
        layer_id: str = None,
        feature_id: int = None,
    ):
        """
        Return basic raster statistics for boundary feature.
        """

        params = QueryBoundaryFeatureSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        anomaly = data.get("anomaly", None)
        anomaly_type = data.get("anomaly_type", None)
        diff_year = data.get("diff_year", None)

        product_queryset = ProductRaster.objects.filter(product__product_id=product_id)

        product_dataset = get_object_or_404(product_queryset, date=date)

        boundary_layer = BoundaryLayer.objects.get(layer_id=layer_id)
        boundary_features = BoundaryFeature.objects.filter(
            boundary_layer=boundary_layer
        )
        boundary_feature = get_object_or_404(boundary_features, feature_id=feature_id)
        print(boundary_feature)
        if not settings.USE_S3:
            path = product_dataset.file_object.path
        if settings.USE_S3:
            path = f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{product_dataset.file_object.name}"

        try:
            with COGReader(path) as product_src:
                feat = product_src.feature(
                    json.loads(boundary_feature.geom.geojson), max_size=1024
                )
                data = feat.as_masked()

                if type(data.mean()) == np.ma.core.MaskedConstant:
                    result = {"value": "No Data"}
                    return Response(result)
                mean = float(
                    Decimal(str(data.mean()))
                    * Decimal(str(product_dataset.product.variable.scale))
                )
                _min = float(
                    Decimal(str(data.min()))
                    * Decimal(str(product_dataset.product.variable.scale))
                )
                _max = float(
                    Decimal(str(data.max()))
                    * Decimal(str(product_dataset.product.variable.scale))
                )
                stdev = float(
                    Decimal(str(data.std()))
                    * Decimal(str(product_dataset.product.variable.scale))
                )

            if cropmask_id != "no-mask":
                mask_queryset = CropmaskRaster.objects.all()
                mask_dataset = get_object_or_404(
                    mask_queryset,
                    product__product_id=product_id,
                    crop_mask__cropmask_id=cropmask_id,
                )

                if not settings.USE_S3:
                    mask_path = mask_dataset.file_object.path
                if settings.USE_S3:
                    mask_path = f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{mask_dataset.file_object.name}"

                with COGReader(mask_path) as mask_src:
                    mask_feat = mask_src.feature(
                        json.loads(boundary_feature.geom.geojson), max_size=1024
                    )
                    mask_data = mask_feat.as_masked()
                    print(data.shape, mask_data.shape)
                    data = data * mask_data

                    mean = float(
                        Decimal(str(data.mean()))
                        * Decimal(str(product_dataset.product.variable.scale))
                    )
                    _min = float(
                        Decimal(str(data.min()))
                        * Decimal(str(product_dataset.product.variable.scale))
                    )
                    _max = float(
                        Decimal(str(data.max()))
                        * Decimal(str(product_dataset.product.variable.scale))
                    )
                    stdev = float(
                        Decimal(str(data.std()))
                        * Decimal(str(product_dataset.product.variable.scale))
                    )

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

                with COGReader(baseline_path) as baseline_src:
                    baseline_feat = baseline_src.feature(
                        json.loads(boundary_feature.geom.geojson), max_size=1024
                    )
                    baseline_data = baseline_feat.as_masked()

                if cropmask_id != "no-mask":
                    # mask baseline data
                    baseline_data = baseline_data * mask_data

                mean = data.mean() - baseline_data.mean()
                _min = data.min() - baseline_data.min()
                _max = data.max() - baseline_data.max()
                stdev = data.std() - baseline_data.std()

                mean = float(
                    Decimal(str(mean))
                    * Decimal(str(product_dataset.product.variable.scale))
                )
                _min = float(
                    Decimal(str(_min))
                    * Decimal(str(product_dataset.product.variable.scale))
                )
                _max = float(
                    Decimal(str(_max))
                    * Decimal(str(product_dataset.product.variable.scale))
                )
                stdev = float(
                    Decimal(str(stdev))
                    * Decimal(str(product_dataset.product.variable.scale))
                )

            if type(mean) != np.ma.core.MaskedConstant:
                result = {"min": _min, "max": _max, "mean": mean, "std": stdev}
            else:
                result = {"value": "No Data"}
        except InvalidOperation:
            result = {"value": "No Data"}

        return Response(result)
