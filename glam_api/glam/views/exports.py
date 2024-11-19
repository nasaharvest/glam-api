import json
from decimal import Decimal

import numpy as np

from rio_tiler.io import COGReader

import rasterio
from rasterio import features

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from django_q.tasks import async_task

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.shortcuts import get_object_or_404
from django.conf import settings

from ..models import (
    Product,
    ProductRaster,
    CropMask,
    CropmaskRaster,
    BoundaryLayer,
    BoundaryFeature,
    AnomalyBaselineRaster,
    DataSource,
    ImageExport,
)
from ..serializers import (
    ExportBodySerializer,
    ExportSerializer,
    ExportBoundaryFeatureSerializer,
)


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
    for b in boundary_layers:
        AVAILABLE_BOUNDARY_LAYERS.append(b.layer_id)
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


class ImageExportViewSet(viewsets.ViewSet):
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

    @swagger_auto_schema(
        operation_id="export_custom_feature", request_body=ExportBodySerializer
    )
    def custom_feature_export(self, request):
        """
        Export imagery using provided geometry.
        """

        if request.method == "POST":
            params = ExportBodySerializer(data=request.data)
            params.is_valid(raise_exception=True)
            data = params.validated_data
            geom = data.get("geom", None)
            # if feature collection get first feature
            if geom["type"] == "FeatureCollection":
                geom = geom["features"][0]
            if (
                geom["geometry"]["type"] == "Polygon"
                or geom["geometry"]["type"] == "MultiPolygon"
            ):
                new_export = ImageExport()
                new_export.save()
                export_id = str(new_export.id)
                result = {"export_id": export_id}
                print(data)
                task = async_task(
                    "glam.utils.export.image_export",
                    export_id,
                    data,
                    hook="glam.utils.export.upload_export",
                )
                return Response(result)

            else:
                raise APIException(
                    "Geometry must be of type 'Polygon' or 'MultiPolygon"
                )

    @swagger_auto_schema(
        operation_id="export_boundary_feature",
        manual_parameters=[
            product_param,
            date_param,
            boundary_layer_param,
            boundary_feature_param,
        ],
    )
    def boundary_feature_export(
        self,
        request,
        product_id: str = None,
        date: str = None,
        cropmask_id: str = None,
        layer_id: str = None,
        feature_id: int = None,
    ):
        """
        Export imagery using boundary feature.
        """

        params = ExportBoundaryFeatureSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data
        data["product_id"] = product_id
        data["cropmask_id"] = cropmask_id
        data["date"] = date
        data["geom"] = None
        data["layer_id"] = layer_id
        data["feature_id"] = feature_id

        new_export = ImageExport()
        new_export.save()
        export_id = str(new_export.id)
        result = {"export_id": export_id}
        print(data)
        task = async_task(
            "glam.utils.export.image_export",
            export_id,
            data,
            hook="glam.utils.export.upload_export",
        )
        return Response(result)


class GetExportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImageExport.objects.all()
    serializer_class = ExportSerializer
