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

from ..models import BoundaryLayer, Tag
from ..serializers import BoundaryLayerSerializer
from ..filters import BoundaryLayerFilter


AVAILABLE_TAGS = list()

try:
    tags = Tag.objects.all()
    for t in tags:
        AVAILABLE_TAGS.append(t.name)
except:
    pass

tag_param = openapi.Parameter(
    'tag',
    openapi.IN_QUERY,
    description="String representing tag(s) to filter products.",
    required=False,
    type=openapi.TYPE_STRING,
    enum=AVAILABLE_TAGS if len(AVAILABLE_TAGS) > 0 else None)


class BoundaryLayerPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'limit'


# @method_decorator(name='list', decorator=cache_page(60*60*24*7))
@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        operation_id="boundary layer list",
        manual_parameters=[tag_param],
        operation_description="Return list of available\
             Boundary Layers."))
# @method_decorator(name='retrieve', decorator=cache_page(60*60*24*7))
@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema(
        operation_id="boundary layer detail",
        operation_description="Return details for specified\
             Boundary Layer."))
class BoundaryLayerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Return available boundary layers.
    """
    queryset = BoundaryLayer.objects.all().prefetch_related(
        'tags', 'source'
    ).order_by('layer_id')
    lookup_field = 'layer_id'
    serializer_class = BoundaryLayerSerializer

    def get_queryset(self):
        accept_language = self.request.META.get('HTTP_ACCEPT_LANGUAGE', None)
        print(accept_language)
        if accept_language:
            translation.activate(accept_language[0:2])
        return self.queryset

    pagination_class = BoundaryLayerPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = BoundaryLayerFilter
    search_fields = ['name']
