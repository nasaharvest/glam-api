from rest_framework import serializers

from rest_pandas.serializers import PandasSerializer

from rio_tiler.colormap import cmap

from .models import (
    DataSource,
    ImageExport,
    Product,
    ProductRaster,
    CropMask,
    BoundaryLayer,
    Tag,
    Variable,
    AnomalyBaselineRaster,
    BoundaryFeature,
    Announcement,
)

AVAILABLE_CMAPS = cmap.list() + ["ndvi"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["name"]


class BoundaryLayerSerializer(serializers.HyperlinkedModelSerializer):
    tags = serializers.StringRelatedField(many=True)
    source = serializers.HyperlinkedRelatedField(
        view_name="datasource-detail", lookup_field="source_id", read_only=True
    )

    class Meta:
        model = BoundaryLayer
        fields = [
            "layer_id",
            "display_name",
            "desc",
            "meta",
            "source",
            "vector_file",
            "date_created",
            "date_added",
            "tags",
        ]


class BoundaryFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoundaryFeature
        fields = ["feature_id", "feature_name"]


class ColormapSerializer(serializers.Serializer):
    colormap = serializers.CharField()


class GetColormapSerializer(serializers.Serializer):
    stretch_min = serializers.FloatField(required=True)
    stretch_max = serializers.FloatField(required=True)
    colormap = serializers.ChoiceField(choices=AVAILABLE_CMAPS, required=False)
    num_values = serializers.IntegerField(required=True, max_value=255)

    def validate(self, data):
        """
        Check that stretch_min is below stretch_max
        """
        if "stretch_min" not in data or "stretch_max" not in data:
            pass
        elif data["stretch_min"] > data["stretch_max"]:
            raise serializers.ValidationError(
                "Max Stretch value must be greater than min"
            )

        return data


class CropMaskSerializer(serializers.HyperlinkedModelSerializer):
    crop_type = serializers.StringRelatedField()
    source = serializers.HyperlinkedRelatedField(
        view_name="datasource-detail", lookup_field="source_id", read_only=True
    )
    tags = serializers.StringRelatedField(many=True)

    class Meta:
        model = CropMask
        fields = [
            "cropmask_id",
            "display_name",
            "crop_type",
            "coverage",
            "mask_type",
            "desc",
            "tags",
            "meta",
            "source",
            "date_created",
            "date_added",
        ]


class DatasetSerializer(serializers.ModelSerializer):
    product_id = serializers.StringRelatedField(source="product")

    class Meta:
        model = ProductRaster
        fields = ["id", "product_id", "date", "prelim", "meta"]


class PointValueSerializer(serializers.Serializer):
    AVAILABLE_CROPMASKS = list()
    ANOMALY_LENGTH_CHOICES = list()
    ANOMALY_TYPE_CHOICES = list()

    try:
        for length in AnomalyBaselineRaster.BASELINE_LENGTH_CHOICES:
            ANOMALY_LENGTH_CHOICES.append(length[0])
        for type in AnomalyBaselineRaster.BASELINE_TYPE_CHOICES:
            ANOMALY_TYPE_CHOICES.append(type[0])
        ANOMALY_TYPE_CHOICES.append("diff")
    except:
        pass

    try:
        cropmasks = CropMask.objects.all()
        for c in cropmasks:
            AVAILABLE_CROPMASKS.append(c.cropmask_id)
    except:
        pass

    anomaly = serializers.ChoiceField(choices=ANOMALY_LENGTH_CHOICES, required=False)
    anomaly_type = serializers.ChoiceField(choices=ANOMALY_TYPE_CHOICES, required=False)
    diff_year = serializers.IntegerField(required=False)
    cropmask_id = serializers.ChoiceField(choices=AVAILABLE_CROPMASKS, required=False)


class PointResponseSerializer(serializers.Serializer):
    value = serializers.FloatField()


class FeatureResponseSerializer(serializers.Serializer):
    mean = serializers.FloatField()
    min = serializers.FloatField()
    max = serializers.FloatField()
    std = serializers.FloatField()


class HistogramResponseSerializer(serializers.Serializer):
    date = serializers.DateField()
    hist = serializers.ListField()
    bin_edges = serializers.ListField()

    # class Meta:
    #     serializer_class = PandasSerializer


class FeatureBodySerializer(serializers.Serializer):
    BASELINE_LENGTH_CHOICES = list()
    BASELINE_TYPE_CHOICES = list()
    AVAILABLE_CROPMASKS = list()
    AVAILABLE_PRODUCTS = list()
    ANOMALY_LENGTH_CHOICES = list()
    ANOMALY_TYPE_CHOICES = list()

    try:
        products = Product.objects.all()
        for c in products:
            AVAILABLE_PRODUCTS.append(c.product_id)
    except:
        pass

    try:
        for length in AnomalyBaselineRaster.BASELINE_LENGTH_CHOICES:
            BASELINE_LENGTH_CHOICES.append(length[0])
            ANOMALY_LENGTH_CHOICES.append(length[0])
        for type in AnomalyBaselineRaster.BASELINE_TYPE_CHOICES:
            BASELINE_TYPE_CHOICES.append(type[0])
            ANOMALY_TYPE_CHOICES.append(type[0])
        ANOMALY_TYPE_CHOICES.append("diff")
    except:
        pass

    try:
        cropmasks = CropMask.objects.all()
        for c in cropmasks:
            AVAILABLE_CROPMASKS.append(c.cropmask_id)
    except:
        pass

    product_id = serializers.ChoiceField(choices=AVAILABLE_PRODUCTS, required=True)
    date = serializers.DateField()
    geom = serializers.JSONField(
        label="GeoJSON",
        help_text='Example: \n \
            {\
                "type": "Feature",\
                "properties": {},\
                "geometry": {\
                    "type": "Polygon",\
                    "coordinates": [\
                        [\
                            [\
                            -76.9423896074295,\
                            38.994889549335134\
                            ],\
                            [\
                            -76.94076955318451,\
                            38.994889549335134\
                            ],\
                            [\
                            -76.94076955318451,\
                            38.99603608019608\
                            ],\
                            [\
                            -76.9423896074295,\
                            38.99603608019608\
                            ],\
                            [\
                            -76.9423896074295,\
                            38.994889549335134\
                            ]\
                        ]\
                    ]\
                }\
            } ',
    )
    baseline = serializers.ChoiceField(
        choices=BASELINE_LENGTH_CHOICES,
        required=False,
        allow_null=True,
    )
    baseline_type = serializers.ChoiceField(
        choices=BASELINE_TYPE_CHOICES, required=False, allow_null=True
    )
    anomaly = serializers.ChoiceField(
        choices=ANOMALY_LENGTH_CHOICES,
        required=False,
        allow_null=True,
    )
    anomaly_type = serializers.ChoiceField(
        choices=ANOMALY_TYPE_CHOICES, required=False, allow_null=True
    )
    diff_year = serializers.IntegerField(required=False, allow_null=True)
    cropmask_id = serializers.ChoiceField(
        choices=AVAILABLE_CROPMASKS, required=False, allow_null=True
    )
    format = serializers.CharField(required=False, allow_null=True)

    # class Meta:
    #     list_serializer_class = PandasSerializer


class GraphicBodySerializer(serializers.Serializer):
    AVAILABLE_CROPMASKS = list()
    AVAILABLE_PRODUCTS = list()
    ANOMALY_LENGTH_CHOICES = list()
    ANOMALY_TYPE_CHOICES = list()
    BOOL_CHOICES = [True, False]
    SIZE_CHOICES = ["tiny", "small", "regular", "large", "xlarge"]

    try:
        products = Product.objects.all()
        for c in products:
            AVAILABLE_PRODUCTS.append(c.product_id)
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

    try:
        cropmasks = CropMask.objects.all()
        for c in cropmasks:
            AVAILABLE_CROPMASKS.append(c.cropmask_id)
    except:
        pass

    product_id = serializers.ChoiceField(choices=AVAILABLE_PRODUCTS, required=True)
    date = serializers.DateField()
    geom = serializers.JSONField(
        label="GeoJSON",
        help_text='Example: \n \
            {\
                "type": "Feature",\
                "properties": {},\
                "geometry": {\
                    "type": "Polygon",\
                    "coordinates": [\
                        [\
                            [\
                            -76.9423896074295,\
                            38.994889549335134\
                            ],\
                            [\
                            -76.94076955318451,\
                            38.994889549335134\
                            ],\
                            [\
                            -76.94076955318451,\
                            38.99603608019608\
                            ],\
                            [\
                            -76.9423896074295,\
                            38.99603608019608\
                            ],\
                            [\
                            -76.9423896074295,\
                            38.994889549335134\
                            ]\
                        ]\
                    ]\
                }\
            } ',
    )
    anomaly = serializers.ChoiceField(
        choices=ANOMALY_LENGTH_CHOICES,
        required=False,
        allow_null=True,
    )
    anomaly_type = serializers.ChoiceField(
        choices=ANOMALY_TYPE_CHOICES, required=False, allow_null=True
    )
    diff_year = serializers.IntegerField(required=False, allow_null=True)
    cropmask_id = serializers.ChoiceField(
        choices=AVAILABLE_CROPMASKS, required=False, allow_null=True
    )
    label = serializers.ChoiceField(
        choices=BOOL_CHOICES, required=False, allow_null=True
    )
    legend = serializers.ChoiceField(
        choices=BOOL_CHOICES, required=False, allow_null=True
    )
    size = serializers.ChoiceField(
        choices=SIZE_CHOICES, required=False, allow_null=True
    )
    format = serializers.CharField(required=False, allow_null=True)

    # class Meta:
    #     list_serializer_class = PandasSerializer


class HistogramBodySerializer(serializers.Serializer):
    AVAILABLE_CROPMASKS = list()
    AVAILABLE_PRODUCTS = list()
    ANOMALY_LENGTH_CHOICES = list()
    ANOMALY_TYPE_CHOICES = list()

    try:
        products = Product.objects.all()
        for c in products:
            AVAILABLE_PRODUCTS.append(c.product_id)
    except:
        pass

    try:
        for length in AnomalyBaselineRaster.BASELINE_LENGTH_CHOICES:
            ANOMALY_LENGTH_CHOICES.append(length[0])
        for type in AnomalyBaselineRaster.BASELINE_TYPE_CHOICES:
            ANOMALY_TYPE_CHOICES.append(type[0])
    except:
        pass

    try:
        cropmasks = CropMask.objects.all()
        for c in cropmasks:
            AVAILABLE_CROPMASKS.append(c.cropmask_id)
    except:
        pass

    product_id = serializers.ChoiceField(choices=AVAILABLE_PRODUCTS, required=True)
    date = serializers.DateField()
    geom = serializers.JSONField(
        label="GeoJSON",
        help_text='Example: \n \
            {\
                "type": "Feature",\
                "properties": {},\
                "geometry": {\
                    "type": "Polygon",\
                    "coordinates": [\
                        [\
                            [\
                            -76.9423896074295,\
                            38.994889549335134\
                            ],\
                            [\
                            -76.94076955318451,\
                            38.994889549335134\
                            ],\
                            [\
                            -76.94076955318451,\
                            38.99603608019608\
                            ],\
                            [\
                            -76.9423896074295,\
                            38.99603608019608\
                            ],\
                            [\
                            -76.9423896074295,\
                            38.994889549335134\
                            ]\
                        ]\
                    ]\
                }\
            } ',
    )
    anomaly = serializers.ChoiceField(
        choices=ANOMALY_LENGTH_CHOICES, required=False, allow_null=True
    )
    anomaly_type = serializers.ChoiceField(
        choices=ANOMALY_TYPE_CHOICES, required=False, allow_null=True
    )
    diff_year = serializers.IntegerField(required=False, allow_null=True)
    cropmask_id = serializers.ChoiceField(
        choices=AVAILABLE_CROPMASKS, required=False, allow_null=True
    )
    num_bins = serializers.IntegerField(required=False, allow_null=True)
    range = serializers.ListField(
        required=False, child=serializers.FloatField(), allow_null=True
    )
    weights = serializers.ListField(
        required=False, child=serializers.FloatField(), allow_null=True
    )
    density = serializers.BooleanField(required=False, default=False, allow_null=True)
    add_years = serializers.ListField(
        required=False, child=serializers.IntegerField(), allow_null=True
    )


class HistogramGETSerializer(serializers.Serializer):
    AVAILABLE_CROPMASKS = list()
    AVAILABLE_PRODUCTS = list()
    ANOMALY_LENGTH_CHOICES = list()
    ANOMALY_TYPE_CHOICES = list()

    try:
        products = Product.objects.all()
        for c in products:
            AVAILABLE_PRODUCTS.append(c.product_id)
    except:
        pass

    try:
        for length in AnomalyBaselineRaster.BASELINE_LENGTH_CHOICES:
            ANOMALY_LENGTH_CHOICES.append(length[0])
        for type in AnomalyBaselineRaster.BASELINE_TYPE_CHOICES:
            ANOMALY_TYPE_CHOICES.append(type[0])
    except:
        pass

    try:
        cropmasks = CropMask.objects.all()
        for c in cropmasks:
            AVAILABLE_CROPMASKS.append(c.cropmask_id)
    except:
        pass

    anomaly = serializers.ChoiceField(
        choices=ANOMALY_LENGTH_CHOICES, required=False, allow_null=True
    )
    anomaly_type = serializers.ChoiceField(
        choices=ANOMALY_TYPE_CHOICES, required=False, allow_null=True
    )
    cropmask_id = serializers.ChoiceField(
        choices=AVAILABLE_CROPMASKS, required=False, allow_null=True
    )
    num_bins = serializers.IntegerField(required=False, allow_null=True)
    range = serializers.CharField(required=False, allow_null=True)
    weights = serializers.CharField(required=False, allow_null=True)
    density = serializers.BooleanField(required=False, default=False, allow_null=True)
    format = serializers.CharField(required=False, allow_null=True)
    add_years = serializers.CharField(required=False, allow_null=True)

    # class Meta:
    #     list_serializer_class = PandasSerializer


class ExportBodySerializer(serializers.Serializer):
    AVAILABLE_PRODUCTS = list()

    try:
        products = Product.objects.all()
        for c in products:
            AVAILABLE_PRODUCTS.append(c.product_id)
    except:
        pass

    product_id = serializers.ChoiceField(choices=AVAILABLE_PRODUCTS, required=True)
    date = serializers.DateField()
    geom = serializers.JSONField(
        label="GeoJSON",
        help_text='Example: \n \
            {\
                "type": "Feature",\
                "properties": {},\
                "geometry": {\
                    "type": "Polygon",\
                    "coordinates": [\
                        [\
                            [\
                            -76.9423896074295,\
                            38.994889549335134\
                            ],\
                            [\
                            -76.94076955318451,\
                            38.994889549335134\
                            ],\
                            [\
                            -76.94076955318451,\
                            38.99603608019608\
                            ],\
                            [\
                            -76.9423896074295,\
                            38.99603608019608\
                            ],\
                            [\
                            -76.9423896074295,\
                            38.994889549335134\
                            ]\
                        ]\
                    ]\
                }\
            } ',
    )


class ExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageExport
        fields = "__all__"


class ProductSerializer(serializers.HyperlinkedModelSerializer):
    # datasets = serializers.HyperlinkedRelatedField(
    #     many=True,
    #     read_only=True,
    #     view_name='productdataset-detail'
    # )
    source = serializers.HyperlinkedRelatedField(
        view_name="datasource-detail", lookup_field="source_id", read_only=True
    )
    variable = serializers.HyperlinkedRelatedField(
        view_name="variable-detail", lookup_field="variable_id", read_only=True
    )
    tags = serializers.StringRelatedField(many=True)

    class Meta:
        model = Product
        fields = [
            "product_id",
            "display_name",
            "desc",
            "tags",
            "meta",
            "variable",
            "source",
            "link",
            "date_start",
            "date_added",
            "composite",
            "composite_period",
        ]


class RGBSerializer(serializers.Serializer):
    stretch_min = serializers.FloatField(required=False)
    stretch_max = serializers.FloatField(required=False)
    tile_size = serializers.IntegerField(required=False)

    def validate(self, data):
        """
        Check that stretch_min is below stretch_max
        """
        if "stretch_min" not in data or "stretch_max" not in data:
            pass
        elif data["stretch_min"] > data["stretch_max"]:
            raise serializers.ValidationError(
                "Max Stretch value must be greater than min"
            )

        return data


class GraphicSerializer(serializers.Serializer):
    ANOMALY_LENGTH_CHOICES = list()
    ANOMALY_TYPE_CHOICES = list()
    SIZE_CHOICES = ["tiny", "small", "regular", "large", "xlarge"]

    try:
        for length in AnomalyBaselineRaster.BASELINE_LENGTH_CHOICES:
            ANOMALY_LENGTH_CHOICES.append(length[0])
        for type in AnomalyBaselineRaster.BASELINE_TYPE_CHOICES:
            ANOMALY_TYPE_CHOICES.append(type[0])
        ANOMALY_TYPE_CHOICES.append("diff")
    except:
        pass

    anomaly = serializers.ChoiceField(choices=ANOMALY_LENGTH_CHOICES, required=False)
    anomaly_type = serializers.ChoiceField(choices=ANOMALY_TYPE_CHOICES, required=False)
    diff_year = serializers.IntegerField(required=False)
    label = serializers.BooleanField(required=False, default=True, allow_null=True)
    legend = serializers.BooleanField(required=False, default=True, allow_null=True)
    size = serializers.ChoiceField(
        choices=SIZE_CHOICES, required=False, default="regular", allow_null=True
    )


class QueryBoundaryFeatureSerializer(serializers.Serializer):
    BASELINE_LENGTH_CHOICES = list()
    BASELINE_TYPE_CHOICES = list()
    ANOMALY_LENGTH_CHOICES = list()
    ANOMALY_TYPE_CHOICES = list()
    SIZE_CHOICES = ["tiny", "small", "regular", "large", "xlarge"]

    try:
        for length in AnomalyBaselineRaster.BASELINE_LENGTH_CHOICES:
            BASELINE_LENGTH_CHOICES.append(length[0])
            ANOMALY_LENGTH_CHOICES.append(length[0])
        for type in AnomalyBaselineRaster.BASELINE_TYPE_CHOICES:
            BASELINE_TYPE_CHOICES.append(type[0])
            ANOMALY_TYPE_CHOICES.append(type[0])
        ANOMALY_TYPE_CHOICES.append("diff")
    except:
        pass

    baseline = serializers.ChoiceField(choices=BASELINE_LENGTH_CHOICES, required=False)
    baseline_type = serializers.ChoiceField(
        choices=BASELINE_TYPE_CHOICES, required=False
    )
    anomaly = serializers.ChoiceField(choices=ANOMALY_LENGTH_CHOICES, required=False)
    anomaly_type = serializers.ChoiceField(choices=ANOMALY_TYPE_CHOICES, required=False)
    diff_year = serializers.IntegerField(required=False)


class ExportBoundaryFeatureSerializer(serializers.Serializer):
    ANOMALY_LENGTH_CHOICES = list()
    ANOMALY_TYPE_CHOICES = list()
    SIZE_CHOICES = ["tiny", "small", "regular", "large", "xlarge"]

    try:
        for length in AnomalyBaselineRaster.BASELINE_LENGTH_CHOICES:
            ANOMALY_LENGTH_CHOICES.append(length[0])
        for type in AnomalyBaselineRaster.BASELINE_TYPE_CHOICES:
            ANOMALY_TYPE_CHOICES.append(type[0])
        ANOMALY_TYPE_CHOICES.append("diff")
    except:
        pass

    anomaly = serializers.ChoiceField(choices=ANOMALY_LENGTH_CHOICES, required=False)
    anomaly_type = serializers.ChoiceField(choices=ANOMALY_TYPE_CHOICES, required=False)
    diff_year = serializers.IntegerField(required=False)


class TilesSerializer(serializers.Serializer):
    AVAILABLE_CROPMASKS = list()
    ANOMALY_LENGTH_CHOICES = list()
    ANOMALY_TYPE_CHOICES = list()

    try:
        cropmasks = CropMask.objects.all()
        for c in cropmasks:
            AVAILABLE_CROPMASKS.append(c.cropmask_id)
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

    anomaly = serializers.ChoiceField(choices=ANOMALY_LENGTH_CHOICES, required=False)
    anomaly_type = serializers.ChoiceField(choices=ANOMALY_TYPE_CHOICES, required=False)
    diff_year = serializers.IntegerField(required=False)
    cropmask_id = serializers.ChoiceField(choices=AVAILABLE_CROPMASKS, required=False)
    cropmask_threshold = serializers.FloatField(required=False)
    colormap = serializers.ChoiceField(choices=AVAILABLE_CMAPS, required=False)
    stretch_min = serializers.FloatField(required=False)
    stretch_max = serializers.FloatField(required=False)
    tile_size = serializers.IntegerField(required=False)

    def validate(self, data):
        """
        Check that stretch_min is below stretch_max
        """
        if "stretch_min" not in data or "stretch_max" not in data:
            pass
        elif data["stretch_min"] > data["stretch_max"]:
            raise serializers.ValidationError(
                "Max Stretch value must be greater than min"
            )

        return data


class SourceSerializer(serializers.HyperlinkedModelSerializer):
    tags = serializers.StringRelatedField(many=True)

    class Meta:
        model = DataSource
        fields = ["source_id", "display_name", "desc", "link", "logo", "tags"]


class VariableSerializer(serializers.HyperlinkedModelSerializer):
    tags = serializers.StringRelatedField(many=True)

    class Meta:
        model = Variable
        fields = [
            "variable_id",
            "display_name",
            "desc",
            "tags",
            "scale",
            "units",
            "unit_abbr",
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    tags = serializers.StringRelatedField(many=True)

    class Meta:
        model = Announcement
        fields = [
            "header",
            "message",
            "date",
            "days_to_expire",
            "sticky",
            "tags",
            "image",
        ]
