# from rest_framework import viewsets
# from rest_framework.response import Response

# from drf_yasg.utils import swagger_auto_schema

# from django.shortcuts import get_object_or_404
# from django.utils.decorators import method_decorator
# from django.views.decorators.cache import cache_page

# from ..mixins import MultiRetrieveView
# from ..models import ProductDataset
# from ..serializers import DatasetStatsSerializer


# @method_decorator(name='retrieve', decorator=cache_page(60*60*24*7))
# @method_decorator(
#     name='retrieve',
#     decorator=swagger_auto_schema(
#         operation_id="dataset stats"))
# class DatasetStatsViewSet(viewsets.ViewSet):

#     def retrieve(self, request, product_id: str = None, date: str = None):
#         """
#         Retrieve summary raster statistics for specified dataset.
#         """
#         queryset = ProductDataset.objects.all()
#         dataset = get_object_or_404(
#             queryset, product__product_id=product_id, date=date)
#         serializer = DatasetStatsSerializer(dataset.raster_stats)
#         return Response(serializer.data)
