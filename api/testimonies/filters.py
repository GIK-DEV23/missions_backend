from django_filters import rest_framework as filters
from base.filters import BaseFilterSet
from testimonies.models import Testimony, Miracle



class TestimonyFilter(BaseFilterSet):
    soul_id = filters.NumberFilter(field_name='soul__id')
    user_id = filters.NumberFilter(field_name='user__id')
    mission_id = filters.NumberFilter(field_name='mission__id')
    created_before = filters.DateTimeFilter(field_name="uploaded_at", lookup_expr="lte")
    created_after = filters.DateTimeFilter(field_name="uploaded_at", lookup_expr="gte")
    search_fields = ["title"]

    class Meta:
        model = Testimony
        fields = ["soul_id", "user_id", "mission_id", "created_before", "created_after", "is_selected", "review_status"]


class MiracleFilter(BaseFilterSet):
    soul_id = filters.NumberFilter(field_name='soul__id')
    user_id = filters.NumberFilter(field_name='user__id')
    mission_id = filters.NumberFilter(field_name='mission__id')
    created_before = filters.DateTimeFilter(field_name="uploaded_at", lookup_expr="lte")
    created_after = filters.DateTimeFilter(field_name="uploaded_at", lookup_expr="gte")
    search_fields = ["title"]

    class Meta:
        model = Miracle
        fields = ["soul_id", "user_id", "mission_id", "created_before", "created_after", "is_selected", "review_status"]
