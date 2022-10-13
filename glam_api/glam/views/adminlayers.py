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

from ..models import AdminLayer, Tag
from ..serializers import AdminLayerSerializer
from ..filters import AdminLayerFilter


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

i18n_param = openapi.Parameter(
    'i18n',
    openapi.IN_QUERY,
    description="Optional parameter to force language if available",
    required=False,
    type=openapi.TYPE_STRING,
    enum=settings.LANGUAGES)


class AdminLayerPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'limit'


# @method_decorator(name='list', decorator=cache_page(60*60*24*7))
@method_decorator(name='list', decorator=vary_on_headers('Accept-Language'))
@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        operation_id="admin layer list",
        manual_parameters=[tag_param, i18n_param],
        operation_description="Return list of available\
             Administrative Layers."))
# @method_decorator(name='retrieve', decorator=cache_page(60*60*24*7))
@method_decorator(name='retrieve', decorator=vary_on_headers('Accept-Language'))
@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema(
        operation_id="admin layer detail",
        manual_parameters=[i18n_param],
        operation_description="Return details for specified\
             Administrative Layer."))
class AdminLayerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Return available administrative layers.
    """
    queryset = AdminLayer.objects.all().prefetch_related(
        'tags', 'source'
    ).order_by('adminlayer_id')
    lookup_field = 'adminlayer_id'
    serializer_class = AdminLayerSerializer

    def get_queryset(self):
        accept_language = self.request.META.get('HTTP_ACCEPT_LANGUAGE', None)
        print(accept_language)
        if accept_language:
            translation.activate(accept_language[0:2])
        return self.queryset

    pagination_class = AdminLayerPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = AdminLayerFilter
    search_fields = ['name']
