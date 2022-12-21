import json
from decimal import Decimal
from attr import dataclass
import numpy as np
import pandas as pd
import datetime

from rio_tiler.io import COGReader
from rio_tiler.utils import get_array_statistics

from rest_framework import viewsets
from rest_framework.decorators import renderer_classes
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.renderers import BrowsableAPIRenderer


from rest_pandas import PandasViewSet
from rest_pandas.renderers import (PandasCSVRenderer,
                                   PandasExcelRenderer, PandasJSONRenderer, PandasTextRenderer,
                                   PandasPNGRenderer, PandasFileRenderer)

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.shortcuts import get_object_or_404, render
from django.conf import settings

from ..models import (ProductRaster, AnomalyBaselineRaster,
                      CropmaskRaster, Product, CropMask, BoundaryLayer, BoundaryFeature)
from ..serializers import (HistogramBodySerializer,
                           HistogramGETSerializer,
                           HistogramResponseSerializer)
from ..renderers import OldGLAMHistRenderer
from ..utils.helpers import get_closest_to_date

AVAILABLE_PRODUCTS = list()
AVAILABLE_CROPMASKS = list()
AVAILABLE_BOUNDARY_LAYERS = list()
ANOMALY_LENGTH_CHOICES = list()
ANOMALY_TYPE_CHOICES = list()

try:
    products = Product.objects.all()
    for p in products:
        AVAILABLE_PRODUCTS.append(p.product_id)
except:
    pass

try:
    cropmasks = CropMask.objects.all()
    for c in cropmasks:
        AVAILABLE_CROPMASKS.append(c.cropmask_id)
except:
    pass

try:
    boundary_layers = BoundaryLayer.objects.all()
    for b in boundary_layers:
        AVAILABLE_BOUNDARY_LAYERS.append(b.layer_id)
except:
    pass

try:
    for length in AnomalyBaselineRaster.BASELINE_LENGTH_CHOICES:
        ANOMALY_LENGTH_CHOICES.append(length[0])
    for type in AnomalyBaselineRaster.BASELINE_TYPE_CHOICES:
        ANOMALY_TYPE_CHOICES.append(type[0])
    ANOMALY_TYPE_CHOICES.append('diff')
except:
    pass

product_param = openapi.Parameter(
    'product_id',
    openapi.IN_PATH,
    description="A unique integer value identifying a dataset.",
    required=True,
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_SLUG,
    enum=AVAILABLE_PRODUCTS if len(AVAILABLE_PRODUCTS) > 0 else None)

cropmask_param = openapi.Parameter(
    'cropmask_id',
    openapi.IN_PATH,
    description="A unique character ID to identify Crop Mask records.",
    required=True,
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_SLUG,
    enum=AVAILABLE_CROPMASKS if len(AVAILABLE_CROPMASKS) > 0 else None)

boundary_layer_param = openapi.Parameter(
    'layer_id',
    openapi.IN_PATH,
    description="A unique character ID to identify Boundary Layer records.",
    required=True,
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_SLUG,
    enum=AVAILABLE_BOUNDARY_LAYERS if len(AVAILABLE_BOUNDARY_LAYERS) > 0 else None)

boundary_feature_param = openapi.Parameter(
    'feature_id',
    openapi.IN_PATH,
    description="Boundary Feature ID.",
    # required=True,
    type=openapi.TYPE_INTEGER
)

date_param = openapi.Parameter(
    'date',
    openapi.IN_PATH,
    description="Dataset Date",
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_DATE
)

anomaly_param = openapi.Parameter(
    'anomaly',
    openapi.IN_QUERY,
    description="String representing anomaly baseline length",
    type=openapi.TYPE_STRING,
    enum=ANOMALY_LENGTH_CHOICES
    if len(ANOMALY_LENGTH_CHOICES) > 0 else None)

diff_year_param = openapi.Parameter(
    'diff_year',
    openapi.IN_QUERY,
    description="Provide year to see difference image from",
    type=openapi.TYPE_INTEGER)

anomaly_type_param = openapi.Parameter(
    'anomaly_type',
    openapi.IN_QUERY,
    description="String representing anomaly type",
    type=openapi.TYPE_STRING,
    enum=ANOMALY_TYPE_CHOICES if len(ANOMALY_TYPE_CHOICES) > 0 else None)

num_bins_param = openapi.Parameter(
    'num_bins',
    openapi.IN_QUERY,
    description="number of bins",
    type=openapi.TYPE_INTEGER,
    format=openapi.TYPE_INTEGER
)

range_param = openapi.Parameter(
    'range',
    openapi.IN_QUERY,
    description="comma separed range values",
    type=openapi.TYPE_STRING,
    format=openapi.TYPE_ARRAY
)

weights_param = openapi.Parameter(
    'weights',
    openapi.IN_QUERY,
    description="comma separed weights values",
    type=openapi.TYPE_STRING,
    format=openapi.TYPE_ARRAY
)

density_param = openapi.Parameter(
    'density',
    openapi.IN_QUERY,
    description="If False, the result will contain "
                "the number of samples in each bin. "
                "If True, the result is the value of"
                " the probability density function at"
                " the bin, normalized such that the integral over the range is 1.",
    type=openapi.TYPE_STRING,
    format=openapi.TYPE_ARRAY
)

format_param = openapi.Parameter(
    'format',
    openapi.IN_QUERY,
    description="output format",
    type=openapi.TYPE_STRING,
    format=openapi.TYPE_STRING
)

add_years_param = openapi.Parameter(
    'add_years',
    openapi.IN_QUERY,
    description="comma separated list of additional years to retreive data (same day)",
    type=openapi.TYPE_STRING,
    format=openapi.TYPE_ARRAY
)


class Histogram(PandasViewSet):

    serializer_class = HistogramResponseSerializer

    renderer_classes = [PandasJSONRenderer, BrowsableAPIRenderer, PandasCSVRenderer,
                        PandasTextRenderer, PandasExcelRenderer,
                        OldGLAMHistRenderer]

    resp_200 = openapi.Response(
        description="Point response",
        schema=HistogramResponseSerializer,
        examples={'application/json':
                  {
                      "date": '2021-01-01',
                      "hist": [
                          3,
                          6,
                          15,
                          21,
                          22,
                          23,
                          25,
                          32,
                          34,
                          35,
                          41,
                          42,
                          52,
                          54,
                          55
                      ],
                      "bin_edges": [
                          0,
                          10,
                          20,
                          30,
                          40,
                          50,
                          60,
                          70,
                          80,
                          90,
                          100,
                          110,
                          120,
                          130,
                          140,
                          150
                      ]
                  }
                  }
    )

    @swagger_auto_schema(
        manual_parameters=[],
        operation_id="custom histogram",
        request_body=HistogramBodySerializer,
        responses={200: resp_200})
    def custom_feature_histogram(self, request):
        """
        Compute histogram for specified polygon. (Using numpy.histogram)
        """

        if request.method == 'POST':

            params = HistogramBodySerializer(data=request.data)
            params.is_valid(raise_exception=True)
            data = params.validated_data

            # raster parameters
            product_id = data.get('product_id', None)
            product = Product.objects.get(product_id=product_id)

            date = data.get('date', None)
            geom = data.get('geom', None)
            geom = geom['geometry']

            anomaly = data.get('anomaly', None)
            anomaly_type = data.get('anomaly_type', None)
            diff_year = data.get('diff_year', None)

            cropmask = data.get('cropmask_id', None)
            if cropmask == 'no-mask':
                cropmask = None

            # histogram parameters
            hist_bins = data.get('num_bins', 10)
            hist_range = data.get('range', None)

            if hist_range:
                hist_range = [
                    float(float(r) / product.variable.scale) for r in hist_range]
            hist_weights = data.get('weights', None)
            hist_density = data.get('density', None)

            hist_options = {
                "bins": hist_bins,
                "range": hist_range,
                "weights": hist_weights,
                "density": hist_density
            }

            years = data.get('add_years', None)
            if years:
                years.append(date.year)
            else:
                years = [date.year]

            month = date.month
            day = date.day

            product_queryset = ProductRaster.objects.filter(
                product=product
            )

            resp_list = []

            for year in years:
                new_date = datetime.date(int(year), month, day)
                product_dataset = get_closest_to_date(
                    product_queryset, new_date)

                if not settings.USE_S3_RASTERS:
                    path = product_dataset.file_object.path
                if settings.USE_S3_RASTERS:
                    path = product_dataset.file_object.url

                if geom['type'] == 'Polygon' or geom['type'] == 'MultiPolygon':

                    with COGReader(path) as product_src:
                        feat = product_src.feature(geom, max_size=1024)
                        data = feat.as_masked()

                    if cropmask:
                        mask_queryset = CropmaskRaster.objects.all()
                        mask_dataset = get_object_or_404(
                            mask_queryset,
                            product__product_id=product_id,
                            crop_mask__cropmask_id=cropmask)

                        if not settings.USE_S3_RASTERS:
                            mask_path = mask_dataset.file_object.path
                        if settings.USE_S3_RASTERS:
                            mask_path = mask_dataset.file_object.url

                        with COGReader(mask_path) as mask_src:
                            mask_feat = mask_src.feature(geom, max_size=1024)
                            mask_data = mask_feat.as_masked()

                            data = data * mask_data

                    if anomaly_type:
                        anom_type = anomaly_type if anomaly_type else 'mean'

                        if anom_type == 'diff':
                            new_year = diff_year
                            new_date = product_dataset.date.replace(
                                year=new_year)
                            anomaly_queryset = ProductRaster.objects.filter(
                                product__product_id=product_id)
                            closest = get_closest_to_date(
                                anomaly_queryset, new_date)
                            try:
                                anomaly_dataset = get_object_or_404(
                                    product_queryset,
                                    date=new_date)
                            except:
                                anomaly_dataset = closest
                        else:
                            doy = product_dataset.date.timetuple().tm_yday
                            if product_id == 'swi':
                                swi_baselines = np.arange(1, 366, 5)
                                idx = (np.abs(swi_baselines - doy)).argmin()
                                doy = swi_baselines[idx]
                            if product_id == 'chirps':
                                doy = int(str(date.month)+f'{date.day:02d}')
                            anomaly_queryset = AnomalyBaselineRaster.objects.all()
                            anomaly_dataset = get_object_or_404(
                                anomaly_queryset,
                                product__product_id=product_id,
                                day_of_year=doy,
                                baseline_length=anomaly,
                                baseline_type=anom_type,
                            )

                        if not settings.USE_S3_RASTERS:
                            baseline_path = anomaly_dataset.file_object.path
                        if settings.USE_S3_RASTERS:
                            baseline_path = anomaly_dataset.file_object.url

                        with COGReader(baseline_path) as baseline_src:
                            baseline_feat = baseline_src.feature(
                                geom, max_size=1024)
                            baseline_data = baseline_feat.as_masked()

                        if cropmask:
                            # mask baseline data
                            baseline_data = baseline_data * mask_data

                        data = data - baseline_data

                    stats = get_array_statistics(data, **hist_options)
                    hist = stats[0]['histogram'][0]
                    bin_edges = stats[0]['histogram'][1]
                    new_bins = [
                        x * product_dataset.product.variable.scale for x in bin_edges]

                    result = {
                        'date': product_dataset.date.strftime('%Y-%d-%m'),
                        'hist': hist,
                        'bin_edges': new_bins
                    }
                    resp_list.append(result)
                else:
                    raise APIException(
                        "Geometry must be of type 'Polygon' or 'MultiPolygon")

            output = pd.DataFrame(resp_list)
            output.set_index('date')
            return Response(output)

    @swagger_auto_schema(
        operation_id="boundary feature histogram",
        manual_parameters=[
            product_param, cropmask_param, boundary_layer_param,
            boundary_feature_param, date_param, format_param,
            anomaly_param, anomaly_type_param, num_bins_param,
            range_param, weights_param, density_param, add_years_param,
            diff_year_param])
    def boundary_feature_histogram(
            self, request, product_id: str = None, cropmask_id: str = None,
            layer_id: str = None, feature_id: int = None,
            date: str = None):
        """
        Compute histogram for boundary feature. (Using numpy.histogram)
        """

        if request.method == 'GET':
            params = HistogramGETSerializer(data=request.query_params)
            params.is_valid(raise_exception=True)
            data = params.validated_data

            product = Product.objects.get(product_id=product_id)

            anomaly = data.get('anomaly', None)
            anomaly_type = data.get('anomaly_type', None)
            diff_year = data.get('diff_year', None)
            # cropmask = data.get('cropmask_id', None)
            cropmask = cropmask_id
            if cropmask == 'no-mask':
                cropmask = None

            # histogram parameters
            hist_bins = data.get('num_bins', 10)
            hist_range = data.get('range', None)
            if hist_range:
                hist_range = hist_range.split(',')
                hist_range = [
                    float(float(r) / product.variable.scale) for r in hist_range]
            hist_weights = data.get('weights', None)
            hist_density = data.get('density', None)

            hist_options = {
                "bins": hist_bins,
                "range": hist_range,
                "weights": hist_weights,
                "density": hist_density
            }

            years = data.get('add_years', None)
            if years:
                years = years.split(',')
                years.append(date.year)
            else:
                years = [date.year]

            month = date.month
            day = date.day

            product_queryset = ProductRaster.objects.filter(
                product=product
            )

            resp_list = []

            for year in years:
                new_date = datetime.date(int(year), month, day)
                product_dataset = get_closest_to_date(
                    product_queryset, new_date)

                boundary_layer = BoundaryLayer.objects.get(layer_id=layer_id)
                boundary_feature = BoundaryFeature.objects.get(
                    boundary_layer=boundary_layer,
                    feature_id=feature_id
                )

                if not settings.USE_S3_RASTERS:
                    path = product_dataset.file_object.path
                if settings.USE_S3_RASTERS:
                    path = product_dataset.file_object.url

                geom = json.loads(boundary_feature.geom.geojson)

                with COGReader(path) as product_src:
                    feat = product_src.feature(geom, max_size=1024)
                    data = feat.as_masked()

                if cropmask:
                    mask_queryset = CropmaskRaster.objects.all()
                    mask_dataset = get_object_or_404(
                        mask_queryset,
                        product__product_id=product_id,
                        crop_mask__cropmask_id=cropmask)

                    if not settings.USE_S3_RASTERS:
                        mask_path = mask_dataset.file_object.path
                    if settings.USE_S3_RASTERS:
                        mask_path = mask_dataset.file_object.url

                    with COGReader(mask_path) as mask_src:
                        mask_feat = mask_src.feature(geom, max_size=1024)
                        mask_data = mask_feat.as_masked()

                        data = data * mask_data

                if anomaly_type:
                    anom_type = anomaly_type if anomaly_type else 'mean'

                    if anom_type == 'diff':
                        new_year = diff_year
                        new_date = product_dataset.date.replace(year=new_year)
                        anomaly_queryset = ProductRaster.objects.filter(
                            product__product_id=product_id)
                        closest = get_closest_to_date(
                            anomaly_queryset, new_date)
                        try:
                            anomaly_dataset = get_object_or_404(
                                product_queryset,
                                date=new_date)
                        except:
                            anomaly_dataset = closest
                    else:
                        doy = product_dataset.date.timetuple().tm_yday
                        if product_id == 'swi':
                            swi_baselines = np.arange(1, 366, 5)
                            idx = (np.abs(swi_baselines - doy)).argmin()
                            doy = swi_baselines[idx]
                        if product_id == 'chirps':
                            doy = int(str(date.month)+f'{date.day:02d}')
                        anomaly_queryset = AnomalyBaselineRaster.objects.all()
                        anomaly_dataset = get_object_or_404(
                            anomaly_queryset,
                            product__product_id=product_id,
                            day_of_year=doy,
                            baseline_length=anomaly,
                            baseline_type=anom_type,
                        )

                    if not settings.USE_S3_RASTERS:
                        baseline_path = anomaly_dataset.file_object.path
                    if settings.USE_S3_RASTERS:
                        baseline_path = anomaly_dataset.file_object.url

                    with COGReader(baseline_path) as baseline_src:
                        baseline_feat = baseline_src.feature(
                            geom, max_size=1024)
                        baseline_data = baseline_feat.as_masked()

                    if cropmask:
                        # mask baseline data
                        baseline_data = baseline_data * mask_data

                    data = data - baseline_data

                stats = get_array_statistics(data, **hist_options)
                hist = stats[0]['histogram'][0]
                bin_edges = stats[0]['histogram'][1]
                new_bins = [
                    x * product_dataset.product.variable.scale for x in bin_edges]

                result = {
                    'date': product_dataset.date.strftime('%Y-%d-%m'),
                    'hist': hist,
                    'bin_edges': new_bins
                }
                resp_list.append(result)

            output = pd.DataFrame(resp_list)
            output.set_index('date')
            return Response(output)
