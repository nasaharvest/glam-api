from rest_framework import viewsets
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from ..mixins import MultiRetrieveView
from ..models import BoundaryLayer, BoundaryFeature
from ..serializers import BoundaryFeatureSerializer

AVAILABLE_BOUNDARY_LAYERS = list()

try:
    boundary_layers = BoundaryLayer.objects.all()
    for b in boundary_layers:
        AVAILABLE_BOUNDARY_LAYERS.append(b.layer_id)
except:
    pass

boundary_layer_param = openapi.Parameter(
    "layer_id",
    openapi.IN_PATH,
    description="A unique character ID to identify Boundary Layer records.",
    required=True,
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_SLUG,
    enum=AVAILABLE_BOUNDARY_LAYERS if len(AVAILABLE_BOUNDARY_LAYERS) > 0 else None,
)


@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_id="boundary-features", manual_parameters=[boundary_layer_param]
    ),
)
class BoundaryFeatureViewSet(viewsets.ViewSet):

    def retrieve(self, request, layer_id: str = None):
        """
        Retrieve features belonging to a specified boundary layer.
        """
        boundary_features = (
            BoundaryFeature.objects.all()
            .prefetch_related("boundary_layer")
            .filter(boundary_layer__layer_id=layer_id)
            .values("feature_id", "feature_name", "boundary_layer")
        )
        serializer = BoundaryFeatureSerializer(boundary_features, many=True)
        return Response(serializer.data)
