import json
from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from django_filters.rest_framework import DjangoFilterBackend

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core import serializers
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.gis.geos import GEOSGeometry

import numpy as np
import matplotlib
from matplotlib.colors import ListedColormap

import rasterio
from rio_tiler.io import COGReader

import matplotlib.pyplot as plt
import matplotlib.image as mimage
from matplotlib.offsetbox import AnchoredText
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import matplotlib.ticker as tkr

import shapely
from shapely import wkb, wkt
from shapely.geometry import Polygon, MultiPolygon, shape
from descartes import PolygonPatch

from rasterio.plot import show

from ..renderers import PNGRenderer
from ..serializers import GraphicSerializer, GraphicBodySerializer
from ..mixins import ListViewSet
from ..models import (
    Tag,
    Product,
    ProductRaster,
    CropMask,
    CropmaskRaster,
    BoundaryLayer,
    BoundaryFeature,
    AnomalyBaselineRaster,
    DataSource,
)
from config.utils import get_closest_to_date


def scale_from_extent(extent):
    """
    Return the appropriate scale (e.g. 'i') for the given extent
    expressed in PlateCarree CRS.
    """
    # Default to coarse scale
    scale = "c"

    if extent is not None:
        # Upper limit on extent in degrees.
        scale_limits = (("c", 20.0), ("l", 10.0), ("i", 2.0), ("h", 0.5), ("f", 0.1))

        width = abs(extent[1] - extent[0])
        height = abs(extent[3] - extent[2])
        min_extent = min(width, height)
        if min_extent != 0:
            for scale, limit in scale_limits:
                if min_extent > limit:
                    break

    return scale


AVAILABLE_PRODUCTS = list()
AVAILABLE_CROPMASKS = list()
AVAILABLE_BOUNDARY_LAYERS = list()
ANOMALY_LENGTH_CHOICES = list()
ANOMALY_TYPE_CHOICES = list()
BOOL_CHOICES = [True, False]
SIZE_CHOICES = ["tiny", "small", "regular", "large", "xlarge"]


def get_fig_size(size):
    if size == "tiny":
        return (4, 4)
    if size == "small":
        return (6, 6)
    if size == "regular":
        return (8, 8)
    if size == "large":
        return (10, 10)
    if size == "xlarge":
        return (12, 12)


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
    ANOMALY_TYPE_CHOICES.append("diff")
except:
    pass


class GraphicsViewSet(viewsets.ViewSet):
    renderer_classes = [PNGRenderer]

    # Manually Defined Parameter Schemas
    product_param = openapi.Parameter(
        "product_id",
        openapi.IN_PATH,
        description="A unique integer value identifying a dataset.",
        required=True,
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_SLUG,
        enum=AVAILABLE_PRODUCTS if len(AVAILABLE_PRODUCTS) > 0 else None,
    )

    date_param = openapi.Parameter(
        "date",
        openapi.IN_PATH,
        description="isodate.",
        required=True,
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    )

    cropmask_param = openapi.Parameter(
        "cropmask_id",
        openapi.IN_PATH,
        description="A unique character ID to identify Crop Mask records.",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_SLUG,
        enum=AVAILABLE_CROPMASKS if len(AVAILABLE_CROPMASKS) > 0 else None,
    )

    boundary_layer_param = openapi.Parameter(
        "layer_id",
        openapi.IN_PATH,
        description="A unique character ID to identify Boundary Layer records.",
        required=True,
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_SLUG,
        enum=AVAILABLE_BOUNDARY_LAYERS if len(AVAILABLE_BOUNDARY_LAYERS) > 0 else None,
    )

    boundary_feature_param = openapi.Parameter(
        "feature_id",
        openapi.IN_PATH,
        description="Boundary Feature ID.",
        # required=True,
        type=openapi.TYPE_INTEGER,
    )

    anomaly_param = openapi.Parameter(
        "anomaly",
        openapi.IN_QUERY,
        description="String representing anomaly baseline length",
        type=openapi.TYPE_STRING,
        enum=ANOMALY_LENGTH_CHOICES if len(ANOMALY_LENGTH_CHOICES) > 0 else None,
    )

    anomaly_type_param = openapi.Parameter(
        "anomaly_type",
        openapi.IN_QUERY,
        description="String representing anomaly type",
        type=openapi.TYPE_STRING,
        enum=ANOMALY_TYPE_CHOICES if len(ANOMALY_TYPE_CHOICES) > 0 else None,
    )

    diff_year_param = openapi.Parameter(
        "diff_year",
        openapi.IN_QUERY,
        description="Provide year to see difference image from",
        type=openapi.TYPE_INTEGER,
    )

    label_param = openapi.Parameter(
        "label",
        openapi.IN_QUERY,
        description="Add Label",
        type=openapi.TYPE_BOOLEAN,
        enum=BOOL_CHOICES,
        default=BOOL_CHOICES[0],
    )

    legend_param = openapi.Parameter(
        "legend",
        openapi.IN_QUERY,
        description="Add Legend",
        type=openapi.TYPE_BOOLEAN,
        enum=BOOL_CHOICES,
        default=BOOL_CHOICES[0],
    )

    size_param = openapi.Parameter(
        "size",
        openapi.IN_QUERY,
        description="Graphic Size",
        type=openapi.TYPE_STRING,
        enum=SIZE_CHOICES,
        default=SIZE_CHOICES[2],
    )

    @swagger_auto_schema(
        operation_id="graphic",
        manual_parameters=[
            product_param,
            date_param,
            cropmask_param,
            boundary_layer_param,
            boundary_feature_param,
            anomaly_param,
            anomaly_type_param,
            diff_year_param,
            label_param,
            legend_param,
            size_param,
        ],
    )
    def boundary_feature_graphic(
        self,
        request,
        product_id: str = None,
        date: str = None,
        cropmask_id: str = None,
        layer_id: str = None,
        feature_id: int = None,
    ):
        """
        Generate static image for given boundary feature.
        """
        BLUE = "#97b6e1"
        GRAY = "#999999"
        land = "#efefdb"

        # import time
        # start = time.time()
        params = GraphicSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data

        anomaly = data.get("anomaly", None)
        anomaly_type = data.get("anomaly_type", None)
        diff_year = data.get("diff_year", None)
        label = data.get("label", None)
        legend = data.get("legend", None)
        size = data.get("size", None)
        figsize = get_fig_size(size)

        product = Product.objects.get(product_id=product_id)
        product_datasets = ProductRaster.objects.filter(product=product)
        product_ds = get_object_or_404(product_datasets, date=date)
        product_scale = product.variable.scale
        if anomaly_type:
            product_variable = product.variable.display_name + " Anomaly"
        else:
            product_variable = product.variable.display_name

        def tick_formatter(x, pos):
            t = "{:g}".format(x * product_scale)
            return t

        formatter = tkr.FuncFormatter(tick_formatter)

        boundary_layer = BoundaryLayer.objects.get(layer_id=layer_id)
        boundary_features = BoundaryFeature.objects.filter(
            boundary_layer=boundary_layer
        )
        boundary_feature = get_object_or_404(boundary_features, feature_id=feature_id)
        boundary_feature_name = boundary_feature.feature_name

        # extent=boundary_feature.geom.extent
        extent = [
            boundary_feature.geom.extent[0],
            boundary_feature.geom.extent[2],
            boundary_feature.geom.extent[1],
            boundary_feature.geom.extent[3],
        ]
        scale = scale_from_extent(extent)

        if scale == "f":
            scale_factor = 0
        elif scale == "c":
            scale_factor = 0.1
        else:
            scale_factor = 0.01

        boundary_feature_geom = boundary_feature.geom.simplify(scale_factor)

        with rasterio.Env(**settings.GDAL_CONFIG_OPTIONS) as env:
            with COGReader(
                f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{product_ds.file_object.name}"
            ) as image:
                feat = image.feature(
                    json.loads(boundary_feature_geom.geojson), max_size=1024
                )

            image = feat.as_masked()

            if anomaly_type:
                anom_type = anomaly_type if anomaly_type else "mean"

                if anom_type == "diff":
                    new_year = diff_year
                    new_date = product_ds.date.replace(year=new_year)
                    anomaly_queryset = ProductRaster.objects.filter(
                        product__product_id=product_id
                    )
                    closest = get_closest_to_date(anomaly_queryset, new_date)
                    try:
                        anomaly_ds = get_object_or_404(anomaly_queryset, date=new_date)
                    except:
                        anomaly_ds = closest

                else:
                    doy = product_ds.date.timetuple().tm_yday
                    if product_id == "swi":
                        swi_baselines = np.arange(1, 366, 5)
                        idx = (np.abs(swi_baselines - doy)).argmin()
                        doy = swi_baselines[idx]
                    if product_id == "chirps":
                        doy = int(str(date.month) + f"{date.day:02d}")
                    anomaly_queryset = AnomalyBaselineRaster.objects.all()
                    anomaly_ds = get_object_or_404(
                        anomaly_queryset,
                        product=product,
                        day_of_year=doy,
                        baseline_length=anomaly,
                        baseline_type=anom_type,
                    )

                with COGReader(
                    f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{anomaly_ds.file_object.name}"
                ) as anom_img:
                    anom_feat = anom_img.feature(
                        json.loads(boundary_feature_geom.geojson), max_size=1024
                    )

                image = image - anom_feat.as_masked()

            if cropmask_id != "no-mask":
                mask = CropMask.objects.get(cropmask_id=cropmask_id)
                mask_queryset = CropmaskRaster.objects.all()
                mask_ds = get_object_or_404(
                    mask_queryset, product__product_id=product_id, crop_mask=mask
                )

                with COGReader(
                    f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{mask_ds.file_object.name}"
                ) as mask_img:
                    mask_feat = mask_img.feature(
                        json.loads(boundary_feature_geom.geojson), max_size=1024
                    )

                image = image * mask_feat.as_masked()

            admin_0 = Tag.objects.get(name="ADM0")
            admin_1 = Tag.objects.get(name="ADM1")

            admin_level = None

            if admin_1 in boundary_layer.tags.all():
                admin_level = admin_1
                buff = 1
            elif admin_0 in boundary_layer.tags.all():
                admin_level = admin_0
                buff = 2
            else:
                admin_level = None
                buff = 1

            fig = plt.figure(figsize=figsize)
            ax = fig.add_subplot(1, 1, 1, frameon=False)

            # boundary_feature_buffer = wkt.loads(boundary_feature_geom.buffer(buff).wkt)

            try:
                from shapely import wkt as shapely_wkt
                from shapely.geometry import shape, mapping
                import numpy as np

                # Debug the GEOS geometry
                print(
                    f"Original geometry class: {boundary_feature_geom.__class__.__name__}"
                )
                print(f"Original geometry: {boundary_feature_geom}")

                # Convert to Shapely geometry via WKT
                shapely_geom = shapely_wkt.loads(boundary_feature_geom.wkt)

                # Ensure geometry is valid
                if not shapely_geom.is_valid:
                    shapely_geom = shapely_geom.buffer(0)

                print(f"Shapely geometry class: {shapely_geom.__class__.__name__}")
                print(f"Shapely geometry valid: {shapely_geom.is_valid}")
                print(f"Shapely geometry coords: {list(shapely_geom.exterior.coords)}")

                # Create polygon patches
                feature_fill = PolygonPatch(
                    shapely_geom.__geo_interface__,
                    fc=GRAY,
                    linewidth=0,
                    alpha=0.5,
                    zorder=0.5,
                )
                feature_border = PolygonPatch(
                    shapely_geom.__geo_interface__,
                    color="black",
                    linewidth=1.5,
                    fill=False,
                    alpha=1,
                    zorder=2,
                )

                # Add patches to plot
                ax.add_patch(feature_border)
                ax.add_patch(feature_fill)

            except Exception as e:
                print(f"Error creating polygon patches: {str(e)}")
                # Try alternative approach using direct coordinates
                try:
                    coords = np.array(list(shapely_geom.exterior.coords))
                    feature_fill = plt.Polygon(coords, fc=GRAY, alpha=0.5, zorder=0.5)
                    feature_border = plt.Polygon(
                        coords, ec="black", fc="none", linewidth=1.5, alpha=1, zorder=2
                    )
                    ax.add_patch(feature_fill)
                    ax.add_patch(feature_border)
                except Exception as e:
                    print(f"Failed alternative approach: {str(e)}")
                    raise APIException(
                        f"Could not create boundary visualization: {str(e)}"
                    )

            # Set wider extent using buffer
            boundary_feature_buffer = boundary_feature_geom.buffer(buff)
            x1, y1, x2, y2 = boundary_feature_buffer.extent
            ax.set_xlim([x1, x2])
            ax.set_ylim([y1, y2])

            # remove ticks
            ax.axes.xaxis.set_visible(False)
            ax.axes.yaxis.set_visible(False)

            extent = [
                boundary_feature_geom.extent[0],
                boundary_feature_geom.extent[2],
                boundary_feature_geom.extent[1],
                boundary_feature_geom.extent[3],
            ]

            colormap = (
                product.meta["graphic_anomaly"]
                if anomaly
                else product.meta["graphic_colormap"]
            )
            if product.variable.variable_id == "modis-ndvi" and not anomaly:
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
                x = np.linspace(0, 1, 256)
                cmap_vals = ndvi(x)[:, :]
                ndvi_cm = ListedColormap(cmap_vals)
                colormap = ndvi_cm

            stretch = (
                product.meta["anomaly_stretch"]
                if (anomaly or anomaly_type == "diff")
                else product.meta["default_stretch"]
            )

            image = ax.imshow(
                image[0],
                extent=extent,
                cmap=colormap,
                vmin=stretch[0],
                vmax=stretch[1],
                zorder=1,
            )

            ax.set_facecolor(BLUE)

            if admin_level:
                feature_intersects = BoundaryFeature.objects.filter(
                    boundary_layer__tags=admin_level,
                    geom__intersects=boundary_feature.geom.buffer(buff).envelope,
                )
            else:
                feature_intersects = BoundaryFeature.objects.filter(
                    boundary_layer=boundary_layer,
                    geom__intersects=boundary_feature.geom.buffer(buff).envelope,
                )
                countries = BoundaryFeature.objects.filter(
                    boundary_layer__tags=admin_0,
                    geom__intersects=boundary_feature.geom.buffer(buff).envelope,
                )
                for feature in countries:
                    wktgeom = wkt.loads(feature.geom.simplify(scale_factor).wkt)
                    try:
                        patch = PolygonPatch(
                            wktgeom,
                            fc=land,
                            ec="black",
                            linestyle=":",
                            alpha=1,
                            zorder=0,
                        )
                        ax.add_patch(patch)
                    except:
                        pass

            for feature in feature_intersects:
                wktgeom = wkt.loads(feature.geom.simplify(scale_factor).wkt)
                try:
                    patch = PolygonPatch(
                        wktgeom,
                        fc=land,
                        ec="black",
                        linestyle=":",
                        alpha=1,
                        zorder=0,
                    )
                    ax.add_patch(patch)
                except:
                    pass

            if label:
                feature_label = f"Region: {str(boundary_feature_name)}"
                date_label = f"\nDate: {str(date)}"
                product_label = f"\nProduct: {str(product.display_name)}"
                cropmask_label = (
                    f"\nCrop Mask: {str(mask.display_name)}"
                    if cropmask_id != "no-mask"
                    else ""
                )

                if anomaly_type == "diff":
                    anomaly_label = f"\nAnomaly: Difference Image vs. {diff_year}"
                elif anomaly_type:
                    anomaly_label = f"\nAnomaly: {str(anom_type).capitalize()}"
                else:
                    anomaly_label = ""

                anomaly_duration = f" - {anomaly}" if anomaly else ""

                label = (
                    feature_label
                    + date_label
                    + product_label
                    + anomaly_label
                    + anomaly_duration
                    + cropmask_label
                )

                text = AnchoredText(
                    label, loc="lower right", prop={"size": 8}, frameon=True
                )
                ax.add_artist(text)

            if legend:
                cbaxes = inset_axes(ax, "33%", "3%", loc="upper right", borderpad=1)
                cbaxes.tick_params(labelsize=8)
                cb = fig.colorbar(
                    image, cax=cbaxes, orientation="horizontal", format=formatter
                )
                cb.set_label(label=product_variable, fontsize=8)

            # Handle logo image from URL
            try:
                from urllib.request import urlopen
                from PIL import Image
                import io

                glam_logo = DataSource.objects.get(source_id="glam").logo.url
                with urlopen(glam_logo) as url:
                    logo_data = url.read()
                logo = Image.open(io.BytesIO(logo_data))
                logo = np.array(logo)

                logo_ax = inset_axes(ax, width="15%", height="10%", loc="lower left")
                logo_ax.imshow(logo, alpha=0.75, origin="upper")
                logo_ax.axis("off")
            except Exception as e:
                print(f"Failed to load logo: {str(e)}")
                # Continue without logo if it fails
                pass

            response = HttpResponse(content_type="image/png")

            fig.savefig(
                response,
                transparent=True,
                # facecolor=BLUE,
                bbox_inches="tight",
                pad_inches=0,
            )

            return Response(response)

    @swagger_auto_schema(
        operation_id="custom graphic",
        manual_parameters=[],
        request_body=GraphicBodySerializer,
        # responses={200: resp_200}
    )
    def custom_feature_graphic(self, request):
        """
        Generate static image for custom geometry.
        """
        if request.method == "POST":
            BLUE = "#97b6e1"
            GRAY = "#999999"
            land = "#efefdb"
            # import time
            # start = time.time()
            params = GraphicBodySerializer(data=request.data)
            params.is_valid(raise_exception=True)
            data = params.validated_data

            product_id = data.get("product_id", None)
            date = data.get("date", None)
            geom = data.get("geom", None)
            anomaly = data.get("anomaly", None)
            anomaly_type = data.get("anomaly_type", None)
            diff_year = data.get("diff_year", None)
            cropmask_id = data.get("cropmask_id", "no-mask")

            label = data.get("label", True)
            legend = data.get("legend", True)
            size = data.get("size", "regular")
            figsize = get_fig_size(size)

            product = Product.objects.get(product_id=product_id)
            product_datasets = ProductRaster.objects.filter(product=product)
            product_ds = get_object_or_404(product_datasets, date=date)
            product_scale = product.variable.scale
            if anomaly_type:
                product_variable = product.variable.display_name + " Anomaly"
            else:
                product_variable = product.variable.display_name

            def tick_formatter(x, pos):
                t = "{:g}".format(x * product_scale)
                return t

            formatter = tkr.FuncFormatter(tick_formatter)

            if (
                geom["geometry"]["type"] == "Polygon"
                or geom["geometry"]["type"] == "MultiPolygon"
            ):
                boundary_feature_geom = GEOSGeometry(shape(geom["geometry"]).wkt)

                extent = [
                    boundary_feature_geom.extent[0],
                    boundary_feature_geom.extent[2],
                    boundary_feature_geom.extent[1],
                    boundary_feature_geom.extent[3],
                ]

                scale = scale_from_extent(extent)

                admin_0 = Tag.objects.get(name="ADM0")
                admin_1 = Tag.objects.get(name="ADM1")

                if scale == "f":
                    scale_factor = 0
                    buff = 1
                    admin_level = admin_1
                elif scale == "c":
                    scale_factor = 0.1
                    buff = 2
                    admin_level = admin_0
                else:
                    scale_factor = 0.01
                    buff = 1
                    admin_level = admin_1

                with rasterio.Env(**settings.GDAL_CONFIG_OPTIONS) as env:

                    with COGReader(
                        f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{product_ds.file_object.name}"
                    ) as image:
                        feat = image.feature(
                            json.loads(boundary_feature_geom.geojson), max_size=1024
                        )

                    image = feat.as_masked()

                    if anomaly_type:
                        anom_type = anomaly_type if anomaly_type else "mean"

                        if anom_type == "diff":
                            new_year = diff_year
                            new_date = product_ds.date.replace(year=new_year)
                            anomaly_queryset = ProductRaster.objects.filter(
                                product__product_id=product_id
                            )
                            closest = get_closest_to_date(anomaly_queryset, new_date)

                            try:
                                anomaly_ds = get_object_or_404(
                                    anomaly_queryset, date=new_date
                                )
                            except:
                                anomaly_ds = closest

                        else:
                            doy = product_ds.date.timetuple().tm_yday
                            if product_id == "swi":
                                swi_baselines = np.arange(1, 366, 5)
                                idx = (np.abs(swi_baselines - doy)).argmin()
                                doy = swi_baselines[idx]
                            if product_id == "chirps":
                                doy = int(str(date.month) + f"{date.day:02d}")
                            anomaly_queryset = AnomalyBaselineRaster.objects.all()
                            anomaly_ds = get_object_or_404(
                                anomaly_queryset,
                                product=product,
                                day_of_year=doy,
                                baseline_length=anomaly,
                                baseline_type=anom_type,
                            )

                        with COGReader(
                            f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{anomaly_ds.file_object.name}"
                        ) as anom_img:
                            anom_feat = anom_img.feature(geom, max_size=1024)

                        image = image - anom_feat.as_masked()

                    if cropmask_id != "no-mask":
                        mask = CropMask.objects.get(cropmask_id=cropmask_id)
                        mask_queryset = CropmaskRaster.objects.all()
                        mask_ds = get_object_or_404(
                            mask_queryset,
                            product__product_id=product_id,
                            crop_mask=mask,
                        )

                        with COGReader(
                            f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{mask_ds.file_object.name}"
                        ) as mask_img:
                            mask_feat = mask_img.feature(geom, max_size=1024)

                        image = image * mask_feat.as_masked()

                    boundary_feature_buffer = wkt.loads(
                        boundary_feature_geom.buffer(buff).wkt
                    )

                    fig = plt.figure(figsize=figsize)
                    ax = fig.add_subplot(1, 1, 1, frameon=False)

                    # set wider extent
                    x1, y1, x2, y2 = boundary_feature_buffer.bounds
                    ax.set_xlim([x1, x2])
                    ax.set_ylim([y1, y2])

                    # remove ticks
                    ax.axes.xaxis.set_visible(False)
                    ax.axes.yaxis.set_visible(False)

                    colormap = (
                        product.meta["graphic_anomaly"]
                        if anomaly
                        else product.meta["graphic_colormap"]
                    )
                    if product.variable.variable_id == "modis-ndvi" and not anomaly:
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
                        x = np.linspace(0, 1, 256)
                        cmap_vals = ndvi(x)[:, :]
                        ndvi_cm = ListedColormap(cmap_vals)
                        colormap = ndvi_cm

                    stretch = (
                        product.meta["anomaly_stretch"]
                        if (anomaly or anomaly_type == "diff")
                        else product.meta["default_stretch"]
                    )

                    image = ax.imshow(
                        image[0],
                        extent=extent,
                        cmap=colormap,
                        vmin=stretch[0],
                        vmax=stretch[1],
                        zorder=1,
                    )

                    feature_intersects = BoundaryFeature.objects.filter(
                        boundary_layer__tags=admin_level,
                        geom__intersects=boundary_feature_geom.buffer(buff).envelope,
                    )
                    for feature in feature_intersects:
                        wktgeom = wkt.loads(feature.geom.simplify(scale_factor).wkt)
                        try:
                            patch = PolygonPatch(
                                wktgeom,
                                fc=land,
                                ec="black",
                                linestyle=":",
                                alpha=1,
                                zorder=0,
                            )
                        except:
                            pass
                        ax.add_patch(patch)

                    feature_fill = PolygonPatch(
                        boundary_feature_geom,
                        fc=GRAY,
                        linewidth=0,
                        alpha=0.5,
                        zorder=0.5,
                    )
                    feature_border = PolygonPatch(
                        boundary_feature_geom,
                        color="black",
                        linewidth=1.5,
                        fill=False,
                        alpha=1,
                        zorder=2,
                    )
                    ax.add_patch(feature_border)
                    ax.add_patch(feature_fill)

                    if label:
                        feature_label = f"Region: Custom Geometry"
                        date_label = f"\nDate: {str(date)}"
                        product_label = f"\nProduct: {str(product.display_name)}"
                        cropmask_label = (
                            f"\nCrop Mask: {str(mask.display_name)}"
                            if cropmask_id != "no-mask"
                            else ""
                        )

                        if anomaly_type == "diff":
                            anomaly_label = (
                                f"\nAnomaly: Difference Image vs. {diff_year}"
                            )
                        elif anomaly_type:
                            anomaly_label = f"\nAnomaly: {str(anom_type).capitalize()}"
                        else:
                            anomaly_label = ""

                        anomaly_duration = f" - {anomaly}" if anomaly else ""
                        # anomaly_diff = f'{}'

                        label = (
                            feature_label
                            + date_label
                            + product_label
                            + anomaly_label
                            + anomaly_duration
                            + cropmask_label
                        )

                        text = AnchoredText(
                            label, loc="lower right", prop={"size": 8}, frameon=True
                        )
                        ax.add_artist(text)

                    if legend:
                        cbaxes = inset_axes(
                            ax, "33%", "3%", loc="upper right", borderpad=1
                        )
                        cbaxes.tick_params(labelsize=8)

                        # fig.colorbar(image, cax=cbaxes)
                        cb = fig.colorbar(
                            image,
                            cax=cbaxes,
                            orientation="horizontal",
                            format=formatter,
                        )
                        # cb.ax.xaxis.set_tick_params(color="white")
                        cb.set_label(label=product_variable, fontsize=8)

                    glam_logo = DataSource.objects.get(source_id="glam").logo.url
                    logo = plt.imread(glam_logo)
                    logo_ax = inset_axes(
                        ax, width="15%", height="10%", loc="lower left"
                    )
                    logo_ax.imshow(logo, alpha=0.75, origin="upper")
                    logo_ax.axis("off")

                    response = HttpResponse(content_type="image/png")

                    fig.savefig(
                        response,
                        transparent=True,
                        facecolor=BLUE,
                        bbox_inches="tight",
                        pad_inches=0,
                    )

                    return Response(response)

            else:
                raise APIException(
                    "Geometry must be of type 'Polygon' or 'MultiPolygon"
                )
