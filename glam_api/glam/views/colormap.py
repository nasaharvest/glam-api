import numpy as np
from typing import List, Tuple, TypeVar, Dict, Any

import numpy
import matplotlib

from rest_framework import viewsets, views
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.pagination import PageNumberPagination

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.utils.decorators import method_decorator

from rio_tiler.colormap import cmap

from ..utils import to_uint8
from ..serializers import ColormapSerializer, GetColormapSerializer


Number = TypeVar("Number", int, float)

AVAILABLE_CMAPS = cmap.list() + ["ndvi"]

AVAILABLE_CMAP_TYPES = list()


class ColormapPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "limit"


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(operation_id="colormap list"),
)
class ColormapView(views.APIView):
    """
    Return list of available Colormaps.

    """

    def get(self, request):
        return Response(AVAILABLE_CMAPS)


class GenerateColormap(viewsets.ViewSet):
    renderer_classes = [JSONRenderer]

    stretch_min_param = openapi.Parameter(
        "stretch_min",
        openapi.IN_QUERY,
        description="Minimum stretch range value",
        type=openapi.TYPE_NUMBER,
        required=True,
    )

    stretch_max_param = openapi.Parameter(
        "stretch_max",
        openapi.IN_QUERY,
        description="Maximum stretch range value",
        type=openapi.TYPE_NUMBER,
        required=True,
    )

    colormap_param = openapi.Parameter(
        "colormap",
        openapi.IN_QUERY,
        description="String representing colormap to apply to tile",
        required=False,
        type=openapi.TYPE_STRING,
        enum=AVAILABLE_CMAPS,
    )

    num_values_param = openapi.Parameter(
        "num_values",
        openapi.IN_QUERY,
        description="Number of Values to return",
        required=True,
        type=openapi.TYPE_INTEGER,
    )

    @swagger_auto_schema(
        manual_parameters=[
            stretch_min_param,
            stretch_max_param,
            colormap_param,
            num_values_param,
        ],
        operation_id="generate colormap",
    )
    def retrieve(
        self,
        request,
        stretch_min: Number = None,
        stretch_max: Number = None,
        colormap: str = None,
        num_values: int = 255,
    ) -> List[Dict[str, Any]]:
        """
        Returns a list [{value=pixel value, rgba=rgba tuple}]\
            for given stretch parameters.
        """

        params = GetColormapSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        colormap = data.get("colormap", None)
        stretch_min = data.get("stretch_min", None)
        stretch_max = data.get("stretch_max", None)
        num_values = data.get("num_values", None)

        stretch_range = [stretch_min, stretch_max]

        target_coords = np.linspace(stretch_min, stretch_max, num_values)

        if colormap == "ndvi":
            ndvi = matplotlib.colors.LinearSegmentedColormap.from_list(
                "ndvi",
                [
                    "#fffee1",
                    "#ffe1c8",
                    "#f5c98c",
                    "#ffdd55",
                    "#ebbe37",
                    "#faffb4",
                    "#e6fa9b",
                    "#cdff69",
                    "#aff05a",
                    "#a0f5a5",
                    "#82e187",
                    "#78c878",
                    "#9ec66c",
                    "#8caf46",
                    "#46b928",
                    "#329614",
                    "#147850",
                    "#1e5000",
                    "#003200",
                ],
                256,
            )
            x = numpy.linspace(0, 1, num_values)
            cmap_vals = ndvi(x)[:, :]
            colors = (cmap_vals * 255).astype("uint8")
        else:
            if colormap is not None:
                cm_list = list(cmap.get(colormap).values())
                cm = []
                for i in cm_list:
                    l = list(i)
                    new = [int(x) for x in l]
                    cm.append(new)
                cm = np.array(cm)
            else:
                # assemble greyscale cmap of shape (255, 4)
                cm = np.ones(shape=(255, 4), dtype="uint8") * 255
                cm[:, :-1] = np.tile(
                    np.arange(1, 256, dtype="uint8")[:, np.newaxis], (1, 3)
                )

            cmap_coords = to_uint8(target_coords, *stretch_range) - 1
            colors = cm[cmap_coords]

        values = [
            dict(value=p, rgba=c)
            for p, c in zip(target_coords.tolist(), colors.tolist())
        ]
        payload = {"colormap": values}
        return Response(payload)
