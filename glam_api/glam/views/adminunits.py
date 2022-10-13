from rest_framework import viewsets
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from ..mixins import MultiRetrieveView
from ..models import AdminLayer, AdminUnit
from ..serializers import AdminUnitSerializer

AVAILABLE_ADMINLAYERS = list()

try:
    adminlayers = AdminLayer.objects.all()
    for a in adminlayers:
        AVAILABLE_ADMINLAYERS.append(a.adminlayer_id)
except:
    pass

adminlayer_param = openapi.Parameter(
    'adminlayer_id',
    openapi.IN_PATH,
    description="A unique character ID to identify Administrative Layer records.",
    required=True,
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_SLUG,
    enum=AVAILABLE_ADMINLAYERS if len(AVAILABLE_ADMINLAYERS) > 0 else None)

# @method_decorator(name='retrieve', decorator=cache_page(60*60*24*7))


@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema(
        operation_id="admin units"))
class AdminUnitViewSet(viewsets.ViewSet):

    @swagger_auto_schema(
        manual_parameters=[adminlayer_param]
    )
    def retrieve(self, request, adminlayer_id: str = None):
        """
        Retrieve admin units belonging to a specified admin layer.
        """
        admin_units = AdminUnit.objects.all().prefetch_related(
            'admin_layer'
        ).filter(admin_layer__adminlayer_id=adminlayer_id).values(
            'admin_unit_id', 'admin_unit_name', 'admin_layer'
        )
        serializer = AdminUnitSerializer(admin_units, many=True)
        return Response(serializer.data)
