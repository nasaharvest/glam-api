import datetime

from rest_framework.routers import DefaultRouter, APIRootView

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from django.urls import path, include, register_converter

from .views.sources import SourceViewSet
from .views.products import ProductViewSet, VariableViewSet
from .views.datasets import DatasetViewSet
from .views.cropmasks import CropMaskViewSet
from .views.boundarylayers import BoundaryLayerViewSet
from .views.tiles import Tiles
from .views.colormap import ColormapViewSet, GenerateColormap
from .views.tags import TagViewSet
from .views.point import PointValue
from .views.query import QueryRasterValue
from .views.histogram import Histogram
from .views.zonal_stats import ZonalStatsViewSet
from .views.graphics import GraphicsViewSet
from .views.boundaryfeatures import BoundaryFeatureViewSet
from .views.announcements import AnnouncementViewSet
from .views.exports import ImageExportViewSet, GetExportViewSet


class APIHomeView(APIRootView):
    """
    Browse select API endpoints below.
    """


class CustomRouter(DefaultRouter):
    """
    A router for read-only APIs, which doesn't use trailing slashes.
    """

    APIRootView = APIHomeView


class IsoDateConverter:
    regex = "\d{4}-\d{2}-\d{2}"

    def to_python(self, value):
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()

    def to_url(self, value):
        return str(value)


class FloatConverter:
    regex = "[-+]?[0-9]*\.?[0-9]+"

    def to_python(self, value):
        return float(value)

    def to_url(self, value):
        return str(value)


register_converter(IsoDateConverter, "isodate")
register_converter(FloatConverter, "float")

get_boundary_features = BoundaryFeatureViewSet.as_view({"get": "retrieve"})
get_tiles = Tiles.as_view({"get": "retrieve"})
preview_tiles = Tiles.as_view({"get": "preview"})
get_colormap = GenerateColormap.as_view({"get": "retrieve"})
get_point = PointValue.as_view({"get": "retrieve"})
get_custom_feature_value = QueryRasterValue.as_view({"post": "query_custom_feature"})
get_boundary_feature_value = QueryRasterValue.as_view({"get": "query_boundary_feature"})
get_custom_feature_histogram = Histogram.as_view({"post": "custom_feature_histogram"})
get_boundary_feature_histogram = Histogram.as_view(
    {"get": "boundary_feature_histogram"}
)
get_zonal_stats = ZonalStatsViewSet.as_view({"get": "list"})
get_custom_feature_graphic = GraphicsViewSet.as_view({"post": "custom_feature_graphic"})
get_boundary_feature_graphic = GraphicsViewSet.as_view(
    {"get": "boundary_feature_graphic"}
)
generate_feature_export = ImageExportViewSet.as_view({"get": "boundary_feature_export"})
generate_custom_export = ImageExportViewSet.as_view({"post": "custom_feature_export"})

router = CustomRouter()
router.register(r"announcements", AnnouncementViewSet)
router.register(r"boundary-layers", BoundaryLayerViewSet)
router.register(r"colormaps", ColormapViewSet)
router.register(r"cropmasks", CropMaskViewSet)
router.register(r"datasets", DatasetViewSet)
router.register(r"exports", GetExportViewSet)
router.register(r"products", ProductViewSet)
router.register(r"sources", SourceViewSet)
router.register(r"tags", TagViewSet)
router.register(r"variables", VariableViewSet)


urlpatterns = [
    # path('', include(router.urls)),
    path("colormap", get_colormap, name="colormap"),
    path(
        "boundary-features/<slug:layer_id>/",
        get_boundary_features,
        name="boundary-features",
    ),
    path("graphic/", get_custom_feature_graphic, name="custom-feature-graphic"),
    path(
        "graphic/<slug:product_id>/<isodate:date>/<slug:cropmask_id>/"
        "<slug:layer_id>/<int:feature_id>",
        get_boundary_feature_graphic,
        name="boundary-feature-graphic",
    ),
    path("histogram/", get_custom_feature_histogram, name="custom-feature-histogram"),
    path(
        "histogram/<slug:product_id>/<isodate:date>/<slug:cropmask_id>/"
        "<slug:layer_id>/<int:feature_id>/",
        get_boundary_feature_histogram,
        name="boundary-feature-histogram",
    ),
    path(
        "point/<slug:product_id>/<isodate:date>/<float:lon>/<float:lat>/",
        get_point,
        name="point",
    ),
    path("query/", get_custom_feature_value, name="query-custom-feature"),
    path(
        "query/<slug:product_id>/<isodate:date>/<slug:cropmask_id>/"
        "<slug:layer_id>/<int:feature_id>/",
        get_boundary_feature_value,
        name="query-boundary-feature",
    ),
    path("export/", generate_custom_export, name="export-custom-feature"),
    path(
        "export/<slug:product_id>/<isodate:date>/<slug:cropmask_id>/"
        "<slug:layer_id>/<int:feature_id>/",
        generate_feature_export,
        name="export-boundary-feature",
    ),
    path(
        "tiles/<slug:product_id>/<isodate:date>/preview.png",
        preview_tiles,
        name="tiles-preview",
    ),
    path(
        "tiles/<slug:product_id>/<isodate:date>/<int:z>/<int:x>/<int:y>.png",
        get_tiles,
        name="tiles",
    ),
    path(
        "zonal-stats/<slug:product_id>/<slug:cropmask_id>/"
        "<slug:layer_id>/<int:feature_id>",
        get_zonal_stats,
        name="zonal-stats",
    ),
]
urlpatterns += router.urls

schema_view = get_schema_view(
    openapi.Info(
        title="GLAM API",
        default_version="v2.0",
        description="An API delivering the data and services to the GLAM System.",
    ),
    public=True,
    patterns=[path("", include(urlpatterns))],
)

urlpatterns += [
    path(
        "docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
