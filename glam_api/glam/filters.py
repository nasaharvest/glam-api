from django_filters import rest_framework as filters

from .models import (BoundaryLayer, DataSource, Product, ProductRaster, Tag,
                     Variable, CropMask, Colormap, ZonalStats)


class BoundaryLayerFilter(filters.FilterSet):
    tag = filters.ModelMultipleChoiceFilter(
        field_name='tags__name',
        to_field_name='name',
        label="Tag Name",
        queryset=Tag.objects.all())

    class Meta:
        model = BoundaryLayer
        fields = []


class ColormapFilter(filters.FilterSet):

    class Meta:
        model = Colormap
        fields = ['colormap_type']


class CropMaskFilter(filters.FilterSet):
    tag = filters.ModelMultipleChoiceFilter(
        field_name='tags__name',
        to_field_name='name',
        label="Tag Name",
        queryset=Tag.objects.all())

    class Meta:
        model = CropMask
        fields = []


class SourceFilter(filters.FilterSet):
    tag = filters.ModelMultipleChoiceFilter(
        field_name='tags__name',
        to_field_name='name',
        label="Tag Name",
        queryset=Tag.objects.all())

    class Meta:
        model = DataSource
        fields = []


class VariableFilter(filters.FilterSet):
    tag = filters.ModelMultipleChoiceFilter(
        field_name='tags__name',
        to_field_name='name',
        label="Tag Name",
        queryset=Tag.objects.all())

    class Meta:
        model = Variable
        fields = []


class ProductFilter(filters.FilterSet):
    tag = filters.ModelMultipleChoiceFilter(
        field_name='tags__name',
        to_field_name='name',
        label="Tag Name",
        queryset=Tag.objects.all())

    class Meta:
        model = Product
        fields = []


class DatasetFilter(filters.FilterSet):
    product_id = filters.ModelChoiceFilter(
        field_name='product__product_id',
        to_field_name='product_id',
        label='Product',
        queryset=Product.objects.all())

    date_after = filters.DateFilter(
        field_name='date',
        lookup_expr='gte'
    )

    date_before = filters.DateFilter(
        field_name='date',
        lookup_expr='lte'
    )

    tag = filters.ModelMultipleChoiceFilter(
        field_name='tags__name',
        to_field_name='name',
        label="Tag Name",
        queryset=Tag.objects.all())

    class Meta:
        model = ProductRaster
        fields = []


# class ZonalStatsFilter(filters.FilterSet):

#     date_after = filters.DateFilter(
#         field_name='date',
#         lookup_expr='gte'
#     )

#     date_before = filters.DateFilter(
#         field_name='date',
#         lookup_expr='lte'
#     )

#     class Meta:
#         model = ZonalStats
#         fields = ['date']
