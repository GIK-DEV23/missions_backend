"""
Selectors for testimonies and miracles - simple helpers that return QuerySets or model instances
"""
from typing import Optional
from django.db.models import Q

from base.utils.exceptions import CustomValidationError
from testimonies.filters import TestimonyFilter, MiracleFilter, HighlightFilter
from testimonies.models import Testimony, Miracle, Highlight, TestimonyPhoto, MiraclePhoto, HighlightPhoto


def testimonies_list(filters: Optional[dict] = None):
    qs = Testimony.objects.select_related('soul', 'user', 'mission').all()
    if not filters:
        return qs

    return TestimonyFilter(filters, queryset=qs).qs


def testimony_details(testimony_id: int) -> Testimony:
   try:
         return Testimony.objects.get(id=testimony_id)
   except Testimony.DoesNotExist:
       raise CustomValidationError("Testimony with ID {} does not exist".format(testimony_id))


def miracles_list(filters: Optional[dict] = None):
    qs = Miracle.objects.select_related('soul', 'user', 'mission').all()
    if not filters:
        return qs

    return MiracleFilter(filters, queryset=qs).qs


def miracle_details(miracle_id: int) -> Miracle:
    try:
        return Miracle.objects.get(id=miracle_id)
    except Miracle.DoesNotExist:
        raise CustomValidationError("Miracle with ID {} does not exist".format(miracle_id))


def highlights_list(filters: Optional[dict] = None):
    qs = Highlight.objects.select_related('soul', 'user', 'mission').all()
    if not filters:
        return qs

    return HighlightFilter(filters, queryset=qs).qs


def highlight_details(highlight_id: int) -> Highlight:
    try:
        return Highlight.objects.get(id=highlight_id)
    except Highlight.DoesNotExist:
        raise CustomValidationError("Highlight with ID {} does not exist".format(highlight_id))


def testimony_photos_list(testimony_id: int):
    return TestimonyPhoto.objects.filter(testimony_id=testimony_id)


def miracle_photos_list(miracle_id: int):
    return MiraclePhoto.objects.filter(miracle_id=miracle_id)


def highlight_photos_list(highlight_id: int):
    return HighlightPhoto.objects.filter(highlight_id=highlight_id)
