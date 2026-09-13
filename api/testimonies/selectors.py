"""
Selectors for testimonies and miracles - simple helpers that return QuerySets or model instances
"""
from typing import Optional
from django.db.models import Q

from base.utils.exceptions import NotFoundError
from testimonies.filters import TestimonyFilter, MiracleFilter
from testimonies.models import Testimony, Miracle


def testimonies_list(filters: Optional[dict] = None):
    qs = Testimony.objects.select_related('soul', 'user', 'mission').all()
    if not filters:
        return qs

    return TestimonyFilter(filters, queryset=qs).qs


def testimony_details(testimony_id: int) -> Testimony:
   try:
         return Testimony.objects.get(id=testimony_id)
   except Testimony.DoesNotExist:
       raise NotFoundError("Testimony with ID {} does not exist".format(testimony_id))


def miracles_list(filters: Optional[dict] = None):
    qs = Miracle.objects.select_related('soul', 'user', 'mission').all()
    if not filters:
        return qs

    return MiracleFilter(filters, queryset=qs).qs


def miracle_details(miracle_id: int) -> Miracle:
    try:
        return Miracle.objects.get(id=miracle_id)
    except Miracle.DoesNotExist:
        raise NotFoundError("Miracle with ID {} does not exist".format(miracle_id))
