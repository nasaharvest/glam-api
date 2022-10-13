import datetime

from rest_framework.routers import DefaultRouter

from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from django.urls import path, include, register_converter

from .views.sources import SourceViewSet
from .views.products import ProductViewSet, VariableViewSet
from .views.datasets import DatasetViewSet
from .views.cropmasks import CropMaskViewSet
from .views.adminlayers import AdminLayerViewSet
from .views.tiles import Tiles
from .views.colormap import ColormapViewSet, GenerateColormap
# from .views.dataset_stats import DatasetStatsViewSet
from .views.tags import TagViewSet
from .views.point import PointValue
from .views.feature import FeatureValue
from .views.histogram import Histogram
from .views.zonal_stats import ZonalStatsViewSet
from .views.graphics import GraphicsViewSet
from .views.adminunits import AdminUnitViewSet
from .views.announcements import AnnouncementViewSet
from .views.exports import ImageExportViewSet, GetExportViewSet


class IsoDateConverter:
    regex = '\d{4}-\d{2}-\d{2}'

    def to_python(self, value):
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()

    def to_url(self, value):
        return str(value)


class FloatConverter:
    regex = '[-+]?[0-9]*\.?[0-9]+'

    def to_python(self, value):
        return float(value)

    def to_url(self, value):
        return str(value)


register_converter(IsoDateConverter, 'isodate')
register_converter(FloatConverter, 'float')

get_tiles = Tiles.as_view({'get': 'retrieve'})
preview_tiles = Tiles.as_view({'get': 'preview'})
get_admin_units = AdminUnitViewSet.as_view({'get': 'retrieve'})
get_colormap = GenerateColormap.as_view({'get': 'retrieve'})
# get_dataset_stats = DatasetStatsViewSet.as_view({'get': 'retrieve'})
get_point = PointValue.as_view({'get': 'retrieve'})
get_feature = FeatureValue.as_view({'post': 'retrieve'})
get_admin_feature = FeatureValue.as_view({'get': 'admin_feature'})
get_custom_histogram = Histogram.as_view({'post': 'custom_hist'})
get_admin_histogram = Histogram.as_view({'get': 'admin_hist'})
get_zonal_stats = ZonalStatsViewSet.as_view({'get': 'list'})
get_custom_graphic = GraphicsViewSet.as_view({'post': 'custom_graphic'})
get_admin_graphic = GraphicsViewSet.as_view({'get': 'admin_graphic'})
generate_custom_export = ImageExportViewSet.as_view({'post': 'custom_export'})

router = DefaultRouter()
router.register(r'admin-layers', AdminLayerViewSet)
router.register(r'colormaps', ColormapViewSet)
router.register(r'cropmasks', CropMaskViewSet)
router.register(r'datasets', DatasetViewSet)
router.register(r'products', ProductViewSet)
router.register(r'sources', SourceViewSet)
router.register(r'tags', TagViewSet)
router.register(r'variables', VariableViewSet)
router.register(r'announcements', AnnouncementViewSet)
router.register(r'exports', GetExportViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('admin-units/<slug:adminlayer_id>/',
         get_admin_units, name='admin-units'),
    path('colormap', get_colormap, name='colormap'),
    #     path('dataset-stats/<slug:product_id>/<isodate:date>/', get_dataset_stats,
    #          name='dataset-stats'),
    path('graphic/', get_custom_graphic, name='custom-graphic'),
    path('graphic/<slug:product_id>/<isodate:date>/<slug:cropmask_id>/'
         '<slug:adminlayer_id>/<int:admin_unit>', get_admin_graphic, name='admin-graphic'),
    path('histogram/', get_custom_histogram, name='custom-histogram'),
    path('histogram/<slug:product_id>/<isodate:date>/<slug:cropmask_id>/'
         '<slug:adminlayer_id>/<int:admin_unit>/',
         get_admin_histogram, name='admin-histogram'),
    path('point/<slug:product_id>/<isodate:date>/<float:lon>/<float:lat>/',
         get_point, name='point'),
    path('feature/', get_feature, name='feature'),
    path('feature/<slug:product_id>/<isodate:date>/<slug:cropmask_id>/'
         '<slug:adminlayer_id>/<int:admin_unit>/', get_admin_feature, name='admin-feature'),
    path('export/', generate_custom_export, name='custom-export'),
    path('tiles/<slug:product_id>/<isodate:date>/preview.png',
         preview_tiles, name='tiles-preview'),
    path('tiles/<slug:product_id>/<isodate:date>/<int:z>/<int:x>/<int:y>.png',
         get_tiles, name='tiles'),
    path('zonal-stats/<slug:product_id>/<slug:cropmask_id>/'
         '<slug:adminlayer_id>/<int:admin_unit>', get_zonal_stats, name='zonal-stats')
]

schema_view = get_schema_view(
    openapi.Info(title="GLAM API",
                 default_version='v2.0',
                 description="An API delivering the data and services to the GLAM System."),
    public=True,
    patterns=[path('', include(urlpatterns))],
)

urlpatterns += [
    path('docs/',
         schema_view.with_ui('swagger', cache_timeout=0),
         name='schema-swagger-ui'),
    path('redoc/',
         schema_view.with_ui('redoc', cache_timeout=0),
         name="schema-redoc"),
]
