from typing import Optional
import datetime

from django.db.models import Q
from django.utils import timezone

from authentication.permissions import has_role_type
from souls.models import Soul, ProgressUpdate
from testimonies.models import Testimony, Miracle, Highlight


def _is_special_user(user) -> bool:
    return (
        has_role_type("admin", user=user)
        or has_role_type("superadmin", user=user)
        or has_role_type("staff", user=user)
        or has_role_type("executive", user=user)
    )


def visible_souls(user, include_deleted=False):
    """Personal souls stay visible to the missioner who recorded them, plus
    whoever is assigned to or a co-carer for them (shared record access)."""
    qs = Soul.objects.select_related("location", "mission", "user")
    if not include_deleted:
        qs = qs.filter(deleted_at__isnull=True)
    shared_access = Q(user=user) | Q(assigned_to=user) | Q(co_carers=user)
    if _is_special_user(user):
        return qs.filter(Q(is_personal=False) | shared_access).distinct()
    return qs.filter(shared_access).distinct()


def visible_testimonies(user):
    qs = Testimony.objects.select_related("soul", "user", "mission")
    if _is_special_user(user):
        return qs.filter(Q(is_personal=False) | Q(user=user))
    return qs.filter(user=user)


def visible_miracles(user):
    qs = Miracle.objects.select_related("soul", "user", "mission")
    if _is_special_user(user):
        return qs.filter(Q(is_personal=False) | Q(user=user))
    return qs.filter(user=user)


def visible_highlights(user):
    qs = Highlight.objects.select_related("soul", "user", "mission")
    if _is_special_user(user):
        return qs.filter(Q(is_personal=False) | Q(user=user))
    return qs.filter(user=user)


def visible_progress_updates(user):
    """Check-ins follow their soul's visibility, not an owner field of their own."""
    souls = visible_souls(user).values_list("id", flat=True)
    return ProgressUpdate.objects.select_related("soul").filter(soul_id__in=souls)


def changes_since(user, since: Optional[datetime.datetime], request=None) -> dict:
    cursor = timezone.now()

    souls = visible_souls(user)
    testimonies = visible_testimonies(user)
    miracles = visible_miracles(user)
    highlights = visible_highlights(user)
    progress_updates = visible_progress_updates(user)

    if since:
        souls = souls.filter(updated_at__gte=since)
        testimonies = testimonies.filter(updated_at__gte=since)
        miracles = miracles.filter(updated_at__gte=since)
        highlights = highlights.filter(updated_at__gte=since)
        progress_updates = progress_updates.filter(updated_at__gte=since)

    deleted_soul_ids = []
    if since:
        deleted_soul_ids = list(
            visible_souls(user, include_deleted=True)
            .filter(deleted_at__gte=since)
            .values_list("id", flat=True)
        )

    return {
        "souls": [s.to_dict(request) for s in souls],
        "progress_updates": [p.to_dict(request) for p in progress_updates],
        "testimonies": [t.to_dict(request) for t in testimonies],
        "miracles": [m.to_dict(request) for m in miracles],
        "highlights": [h.to_dict(request) for h in highlights],
        "deleted": {"souls": deleted_soul_ids},
        "cursor": cursor.isoformat(),
    }
