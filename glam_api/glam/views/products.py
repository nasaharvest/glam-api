from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination

from django_filters.rest_framework import DjangoFilterBackend

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.conf import settings
from django.utils import translation

from ..models import Product, Tag, Variable
from ..serializers import ProductSerializer, VariableSerializer
from ..filters import ProductFilter, VariableFilter


AVAILABLE_TAGS = list()

try:
    tags = Tag.objects.all()
    for t in tags:
        AVAILABLE_TAGS.append(t.name)
except:
    pass

tag_param = openapi.Parameter(
    "tag",
    openapi.IN_QUERY,
    description="String representing tag(s) to filter products.",
    required=False,
    type=openapi.TYPE_STRING,
    enum=AVAILABLE_TAGS if len(AVAILABLE_TAGS) > 0 else None,
)


class ProductPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "limit"


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="product list",
        operation_description="Return list of available Products.",
        manual_parameters=[tag_param],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_id="product detail",
        operation_description="Return details for specified Product.",
    ),
)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Product.objects.all()
        .prefetch_related("tags", "source", "variable")
        .order_by("product_id")
    )
    lookup_field = "product_id"
    serializer_class = ProductSerializer

    def get_queryset(self):
        accept_language = self.request.META.get("HTTP_ACCEPT_LANGUAGE", None)
        if accept_language:
            translation.activate(accept_language[0:2])
        return self.queryset

    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "metadata", "tags__name"]


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_id="variable list",
        operation_description="Return list of available Variables.",
        manual_parameters=[tag_param],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_id="variable detail",
        operation_description="Return details for specified Variable.",
    ),
)
class VariableViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Variable.objects.all().prefetch_related("tags").order_by("variable_id")
    lookup_field = "variable_id"
    serializer_class = VariableSerializer

    def get_queryset(self):
        accept_language = self.request.META.get("HTTP_ACCEPT_LANGUAGE", None)
        if accept_language:
            translation.activate(accept_language[0:2])
        return self.queryset

    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = VariableFilter
    search_fields = ["name", "desc", "units" "tags__name"]
