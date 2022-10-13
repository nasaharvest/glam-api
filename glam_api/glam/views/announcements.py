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

from ..models import Announcement
from ..serializers import AnnouncementSerializer


i18n_param = openapi.Parameter(
    'i18n',
    openapi.IN_QUERY,
    description="Optional parameter to force language if available",
    required=False,
    type=openapi.TYPE_STRING,
    enum=settings.LANGUAGES)


@method_decorator(name='list', decorator=vary_on_headers('Accept-Language'))
@method_decorator(
    name='list',
    decorator=swagger_auto_schema(
        operation_id="announcement list",
        manual_parameters=[i18n_param],
        operation_description="Return list of announcements."))
@method_decorator(name='retrieve', decorator=vary_on_headers('Accept-Language'))
@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema(
        operation_id="announcement detail",
        manual_parameters=[i18n_param],
        operation_description="Return details for specified announcement."))
class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Announcement.objects.all().order_by('-date')[:5]
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        accept_language = self.request.META.get('HTTP_ACCEPT_LANGUAGE', None)
        print(accept_language)
        if accept_language:
            translation.activate(accept_language[0:2])
        return self.queryset
