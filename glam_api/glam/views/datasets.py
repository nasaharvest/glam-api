from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core import serializers
from django.shortcuts import get_object_or_404

from ..models import ProductDataset, Product, Tag
from ..serializers import DatasetSerializer
from ..filters import DatasetFilter
from ..mixins import ListViewSet

AVAILABLE_PRODUCTS = list()
AVAILABLE_TAGS = list()

try:
    products = Product.objects.all()
    for c in products:
        AVAILABLE_PRODUCTS.append(c.product_id)

    tags = Tag.objects.all()
    for t in tags:
        AVAILABLE_TAGS.append(t.name)
except:
    pass


class DatasetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'limit'


product_param = openapi.Parameter(
    'product_id',
    openapi.IN_QUERY,
    description="A unique character ID representing Product of desired dataset(s).",
    required=False,
    type=openapi.TYPE_STRING,
    enum=AVAILABLE_PRODUCTS if len(AVAILABLE_PRODUCTS) > 0 else None)

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

tag_param = openapi.Parameter(
    'tag',
    openapi.IN_QUERY,
    description="String representing tag(s) to filter datasets.",
    required=False,
    type=openapi.TYPE_STRING,
    enum=AVAILABLE_TAGS if len(AVAILABLE_TAGS) > 0 else None)


# @method_decorator(name='list', decorator=cache_page(60*60*24))
@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        operation_id="dataset list",
        manual_parameters=[
            product_param, tag_param, date_after_param, date_before_param
        ]))
class DatasetViewSet(ListViewSet):
    """
    Return list of available Datasets.
    """
    queryset = ProductDataset.objects.all().prefetch_related(
        'product'
    ).order_by('date')
    serializer_class = DatasetSerializer
    pagination_class = DatasetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = DatasetFilter
    search_fields = ['name', 'meta', 'tags__name']
