from rest_framework import viewsets, mixins
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination

from drf_yasg.utils import swagger_auto_schema

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


from ..models import Tag
from ..serializers import TagSerializer
from ..mixins import ListViewSet


class TagPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'limit'

# @method_decorator(name='list', decorator=cache_page(60*60*24*7))


@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        operation_id="tag list",
        operation_description="Return list of available Tags \
            for searching and filtering."))
class TagViewSet(ListViewSet):
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    pagination_class = TagPagination
    filter_backends = [SearchFilter]
    search_fields = ['name']
