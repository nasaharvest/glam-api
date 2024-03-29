from django.shortcuts import get_object_or_404

from rest_framework import viewsets, mixins, serializers
from rest_framework.reverse import reverse


class ListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    A viewset that provides `retrieve`, `create`, and `list` actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """
    pass


class MultipleFieldLookupMixin:
    """
    Apply this mixin to any view or viewset to get multiple field filtering
    based on a `lookup_fields` attribute, 
    instead of the default single field filtering.
    """

    def get_object(self):
        queryset = self.get_queryset()             # Get the base queryset
        queryset = self.filter_queryset(queryset)  # Apply any filter backends
        filter = {}
        for field in self.lookup_field:
            if self.kwargs[field]:  # Ignore empty fields.
                filter[field] = self.kwargs[self.lookup_field]
        obj = get_object_or_404(queryset, **filter)  # Lookup the object
        self.check_object_permissions(self.request, obj)
        return obj


class MultiRetrieveView(
        MultipleFieldLookupMixin,
        mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    pass
