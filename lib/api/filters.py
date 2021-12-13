from django.db import models
from django.db.models.query import QuerySet

from rest_framework import filters
from rest_framework.request import Request
from rest_framework.views import APIView


class FieldValuesFilter(filters.BaseFilterBackend):
    """
    A filter backend that returns instances whose field (query parameter
    `field`) matches one of the provided values (query parameter `values`,
    comma separated). Add to the view a `field_values_map` attribute that maps
    API fields to model fields.

    Differences to `SearchFilter`:
    - Queries target only one field at a time instead of any of the
      view's `search_fields`.
    - Queries use exact matching.
    - When multiple values are provided, the `OR` operator is used instead of
      `AND`.
    """
    def filter_queryset(self, request: Request, queryset: models.QuerySet, view: APIView) -> QuerySet:
        param_field = request.query_params.get('field', '')
        if not param_field:
            return queryset
        field = view.field_values_map[param_field]
        param_values = request.query_params.get('values', '')
        values = [value.strip() for value in param_values.split(',')]
        kwargs = {f'{field}__in': values}
        return queryset.filter(**kwargs)
