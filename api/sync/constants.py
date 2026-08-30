from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class SyncEntity(TextChoices):
    SOUL = "soul", _("Soul")
    CHECK_IN = "check_in", _("Check-in")
    TESTIMONY = "testimony", _("Testimony")
    MIRACLE = "miracle", _("Miracle")
    HIGHLIGHT = "highlight", _("Highlight")


class SyncOp(TextChoices):
    CREATE = "create", _("Create")
    UPDATE = "update", _("Update")
    DELETE = "delete", _("Delete")


class SyncMutationStatus(TextChoices):
    APPLIED = "applied", _("Applied")
    DUPLICATE = "duplicate", _("Duplicate")
    CONFLICT = "conflict", _("Conflict")
    REJECTED = "rejected", _("Rejected")
