from datetime import datetime
from typing import Mapping, Union, Tuple, TypeVar

from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer

from rest_pandas import PandasViewSet
from rest_pandas.renderers import (PandasCSVRenderer,
                                   PandasExcelRenderer, PandasJSONRenderer, PandasTextRenderer)

from django_filters.rest_framework import DjangoFilterBackend

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import F


from ..serializers import ZStatsSerializer, ZStatsPandasSerializer, ZStatsParamSerializer
from ..renderers import OldGLAMZStatsRenderer
from ..mixins import ListViewSet
from ..models import (ZonalStats, Product, CropMask, BoundaryLayer)

AVAILABLE_PRODUCTS = list()
AVAILABLE_CROPMASKS = list()
AVAILABLE_BOUNDARY_LAYERS = list()

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

product_param = openapi.Parameter(
    'product_id',
    openapi.IN_PATH,
    description="A unique integer value identifying a dataset.",
    required=True,
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_SLUG,
    enum=AVAILABLE_PRODUCTS if len(AVAILABLE_PRODUCTS) > 0 else None)

cropmask_param = openapi.Parameter(
    'cropmask_id',
    openapi.IN_PATH,
    description="A unique character ID to identify Crop Mask records.",
    required=True,
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_SLUG,
    enum=AVAILABLE_CROPMASKS if len(AVAILABLE_CROPMASKS) > 0 else None)

boundary_layer_param = openapi.Parameter(
    'layer_id',
    openapi.IN_PATH,
    description="A unique character ID to identify Boundary Layer records.",
    required=True,
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_SLUG,
    enum=AVAILABLE_BOUNDARY_LAYERS if len(AVAILABLE_BOUNDARY_LAYERS) > 0 else None)

boundary_feature_param = openapi.Parameter(
    'feature_id',
    openapi.IN_PATH,
    description="Boundary Feature ID.",
    # required=True,
    type=openapi.TYPE_INTEGER
)

date_after_param = openapi.Parameter(
    'date_after',
    openapi.IN_QUERY,
    description="Filter Date From.",
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_DATE
)

date_before_param = openapi.Parameter(
    'date_before',
    openapi.IN_QUERY,
    description="Filter Date Before.",
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_DATE
)

format_param = openapi.Parameter(
    'format',
    openapi.IN_QUERY,
    description="output format",
    type=openapi.TYPE_STRING,
    format=openapi.TYPE_STRING
)


class ZStatsPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'limit'


# @method_decorator(name='list', decorator=cache_page(60*60*24))
class ZonalStatsViewSet(PandasViewSet):

    queryset = ZonalStats.objects.all().prefetch_related(
        'product_raster', 'product_raster__product',
        'cropmask_raster', 'cropmask_raster__crop_mask',
        'boundary_raster', 'boundary_raster__boundary_layer'
    )
    pagination_class = ZStatsPagination
    serializer_class = ZStatsPandasSerializer

    renderer_classes = [PandasJSONRenderer, PandasCSVRenderer,
                        PandasTextRenderer, OldGLAMZStatsRenderer,
                        PandasExcelRenderer, BrowsableAPIRenderer]

    @swagger_auto_schema(
        operation_id="zonal stats",
        manual_parameters=[
            product_param, cropmask_param, boundary_layer_param,
            boundary_feature_param, date_after_param, date_before_param,
            format_param]
    )
    def list(
            self, request, product_id: str = None, cropmask_id: str = None,
            layer_id: str = None, feature_id: int = None,
            date_after: str = None, date_before: str = None):
        """
        Return list of Zonal Statistics for specified \
            Dataset, Cropmask and Boundary Layer
        """
        if cropmask_id == 'no-mask':
            queryset = self.get_queryset().filter(
                product_raster__product__product_id=product_id,
                cropmask_raster=None,
                boundary_raster__boundary_layer__layer_id=layer_id,
                feature_id=feature_id).order_by('date')
        else:
            queryset = self.get_queryset().filter(
                product_raster__product__product_id=product_id,
                cropmask_raster__crop_mask__cropmask_id=cropmask_id,
                boundary_raster__boundary_layer__layer_id=layer_id,
                feature_id=feature_id).order_by('date')

        # remove duplicate records
        queryset = queryset.distinct(
            'product_raster', 'cropmask_raster', 'boundary_raster',
            'feature_id', 'arable_pixels', 'percent_arable',
            'mean_value', 'date')

        params = ZStatsParamSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        date_after = data.get('date_after', None)
        date_before = data.get('date_before', None)
        format = data.get('format', None)

        # print(format)
        # if format == 'json':
        #     print('here')
        #     serializer_class = ZStatsSerializer

        if date_after and date_before:
            queryset = queryset.filter(date__range=(date_after, date_before))
        elif date_after and not date_before:
            queryset = queryset.filter(date__gte=date_after)
        elif not date_after and date_before:
            queryset = queryset.filter(date__lte=date_before)

        # disable pagination for pandas renderers

        # page = self.paginate_queryset(queryset)

        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)
