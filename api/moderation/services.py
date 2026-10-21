"""Moderation writes: the report lifecycle and account erasure."""

import logging
from datetime import timedelta
from typing import Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audit_logs.constants import ActionType
from audit_logs.services import log_audit_event, log_moderation_action
from base.utils.exceptions import (
    CustomValidationError,
    ForbiddenError,
    handle_cleaning_error,
)
from moderation.constants import (
    ANONYMIZED_NAME,
    GRACE_PERIOD_DAYS,
    DeletionStatus,
    REMOVABLE_CONTENT_TYPES,
    ReportableContentType,
    ReportStatus,
    TERMINAL_REPORT_STATUSES,
)
from moderation.models import ContentReport, UserDeletion
from moderation.selectors import content_exists, get_report, get_user_deletion

logger = logging.getLogger(__name__)

#: Written over a deleted registrant's required phone column. The column is
#: non-null and format-validated, so erasure cannot simply blank it.
PLACEHOLDER_PHONE = "+254700000000"


# ─── Reports ──────────────────────────────────────────────────────────────────

def create_report(reporter, data: dict) -> ContentReport:
    """Record a report.

    Idempotent by ``client_id`` so a report queued offline on mobile and
    retried after a dropped response is stored once, matching how souls and
    personal missions already de-duplicate. Also idempotent by
    (reporter, content_type, content_id) while a previous report is still
    open, enforced by a DB constraint and short-circuited here so the caller
    gets its existing report back instead of a 400.
    """
    data = dict(data)
    client_id = data.pop("client_id", None)
    content_type = data["content_type"]
    content_id = data["content_id"]

    if client_id is not None:
        existing = ContentReport.objects.filter(client_id=client_id).first()
        if existing is not None:
            return existing

    if not content_exists(content_type, content_id):
        raise CustomValidationError(
            "No {} found with id {}".format(content_type, content_id)
        )

    if reporter is not None:
        open_report = ContentReport.objects.filter(
            reporter=reporter,
            content_type=content_type,
            content_id=content_id,
            status__in=[ReportStatus.PENDING, ReportStatus.UNDER_REVIEW],
        ).first()
        if open_report is not None:
            return open_report

    try:
        report = ContentReport(
            client_id=client_id,
            reporter=reporter,
            content_type=content_type,
            content_id=content_id,
            reason=data["reason"],
            details=data.get("details") or "",
        )
        report.full_clean(exclude=["reporter"])
        report.save()
    except ValidationError as e:
        raise CustomValidationError(handle_cleaning_error(e))
    return report


def _takedown_content(reviewer, report: ContentReport, notes: str) -> None:
    """Take a reported submission off every published surface.

    Deliberately not a delete: the row stays as the evidence behind the
    decision, and a wrong call can be undone by re-approving. Clearing
    ``is_selected`` matters because a featured testimony is what the mobile
    home screen renders, so leaving it set would keep removed content on the
    front page.
    """
    from testimonies.constants import ReviewStatus
    from testimonies.models import Miracle, Testimony

    model = Testimony if report.content_type == ReportableContentType.TESTIMONY else Miracle
    obj = model.objects.filter(id=report.content_id).first()
    if obj is None:
        # Already gone; the report still closes.
        return

    previous_status = obj.review_status
    obj.review_status = ReviewStatus.REJECTED
    obj.rejection_reason = notes or "Removed following a content report"
    obj.is_archived = True
    update_fields = ["review_status", "rejection_reason", "is_archived", "updated_at"]
    if hasattr(obj, "is_selected"):
        obj.is_selected = False
        obj.featured_until = None
        update_fields += ["is_selected", "featured_until"]
    obj.save(update_fields=update_fields)

    log_moderation_action(
        user=reviewer,
        action_type=ActionType.REJECT,
        content_type=report.content_type,
        content_id=report.content_id,
        content_title=obj.title,
        previous_status=previous_status,
        new_status=ReviewStatus.REJECTED,
        rejection_reason=obj.rejection_reason,
        details="report #{}".format(report.pk),
    )


@transaction.atomic
def update_report(reviewer, report_id: int, data: dict) -> ContentReport:
    """Move a report through its review lifecycle.

    ``resolved_removed`` is rejected for `soul` and `user` targets: a Soul is a
    pastoral record about a third party and a User is an account, so neither
    can be "taken down". Those reports close as resolved_no_action or
    dismissed with a note, and any real action is taken through its own
    endpoint (soul delete, or the deletion lifecycle below).
    """
    report = get_report(report_id)
    new_status = data.get("status")
    notes = data.get("resolution_notes")

    if new_status == ReportStatus.RESOLVED_REMOVED and (
        report.content_type not in REMOVABLE_CONTENT_TYPES
    ):
        raise CustomValidationError(
            "A {} report cannot resolve as 'resolved_removed'. Use "
            "'resolved_no_action' or 'dismissed' and record what was done in "
            "resolution_notes.".format(report.content_type)
        )

    if report.status in TERMINAL_REPORT_STATUSES and new_status != report.status:
        raise CustomValidationError(
            "Report #{} is already closed as '{}'".format(report.pk, report.status)
        )

    report.status = new_status
    if notes is not None:
        report.resolution_notes = notes

    if new_status in TERMINAL_REPORT_STATUSES:
        report.reviewed_by = reviewer
        report.reviewed_at = timezone.now()

    report.save(update_fields=[
        "status", "resolution_notes", "reviewed_by", "reviewed_at", "updated_at",
    ])

    if new_status == ReportStatus.RESOLVED_REMOVED:
        _takedown_content(reviewer, report, report.resolution_notes)

    return report


def bulk_update_reports(reviewer, ids: List[int], data: dict) -> Dict[str, object]:
    """Apply one decision to many reports.

    A report the decision cannot legally apply to is skipped and reported back
    rather than failing the whole batch, so one `soul` report in a selection
    does not block the rest.
    """
    updated = 0
    skipped: List[int] = []
    for report_id in ids:
        try:
            update_report(reviewer, report_id, data)
            updated += 1
        except (CustomValidationError, Exception) as e:  # noqa: B014
            logger.info("bulk_update_reports skipped report %s: %s", report_id, e)
            skipped.append(report_id)
    return {"updated": updated, "skipped": skipped}


# ─── Account deletion ─────────────────────────────────────────────────────────

def request_deletion(user, reason: Optional[str] = None) -> UserDeletion:
    """Start the erasure clock for the caller's own account."""
    record = get_user_deletion(user.pk)
    now = timezone.now()

    if record is not None:
        if record.status == DeletionStatus.LEGAL_HOLD:
            raise ForbiddenError(
                "This account is on legal hold and cannot be deleted. "
                "Contact an administrator."
            )
        if record.status == DeletionStatus.ERASURE_COMPLETE:
            raise CustomValidationError("This account has already been erased.")
        if record.status in (
            DeletionStatus.DELETION_REQUESTED,
            DeletionStatus.IN_GRACE_PERIOD,
            DeletionStatus.ERASURE_IN_PROGRESS,
        ):
            return record
    else:
        record = UserDeletion(user=user)

    record.status = DeletionStatus.IN_GRACE_PERIOD
    record.requested_at = now
    record.grace_period_ends_at = now + timedelta(days=GRACE_PERIOD_DAYS)
    record.completed_at = None
    record.cancelled_at = None
    record.cancellation_reason = ""
    record.save()

    log_audit_event(
        user=user,
        action_type=ActionType.DELETION,
        action_category="moderation",
        action_description="Requested account deletion; grace period ends {}".format(
            record.grace_period_ends_at.isoformat()
        ),
        is_successful=True,
    )
    return record


def cancel_deletion(actor, user_id: int, reason: str) -> UserDeletion:
    """Call off a pending deletion, by the account owner or an admin."""
    record = get_user_deletion(user_id)
    if record is None:
        raise CustomValidationError("No deletion request exists for this user.")
    if record.status == DeletionStatus.ERASURE_COMPLETE:
        raise CustomValidationError(
            "This account has already been erased; the request cannot be cancelled."
        )

    record.status = DeletionStatus.ACTIVE
    record.cancelled_at = timezone.now()
    record.cancellation_reason = reason
    record.grace_period_ends_at = None
    record.save(update_fields=[
        "status", "cancelled_at", "cancellation_reason", "grace_period_ends_at",
        "updated_at",
    ])

    log_audit_event(
        user=actor,
        action_type=ActionType.MODIFICATION,
        action_category="moderation",
        action_description="Cancelled deletion request for user #{}: {}".format(
            user_id, reason[:150]
        ),
        is_successful=True,
    )
    return record


def set_legal_hold(admin, user_id: int, reason: str) -> UserDeletion:
    """Block erasure for this account until the hold is lifted.

    A hold can be placed on an account that never asked to be deleted, which
    is the point: it has to be possible to preserve an account before anyone
    tries to erase it.
    """
    from users.selectors import user_details

    target = user_details(user_id)
    record = get_user_deletion(user_id) or UserDeletion(user=target)

    if record.status == DeletionStatus.ERASURE_COMPLETE:
        raise CustomValidationError(
            "This account has already been erased; a hold no longer applies."
        )

    record.status = DeletionStatus.LEGAL_HOLD
    record.legal_hold_reason = reason
    record.legal_hold_by = admin
    record.legal_hold_at = timezone.now()
    record.save()

    log_audit_event(
        user=admin,
        action_type=ActionType.MODIFICATION,
        action_category="moderation",
        action_description="Placed legal hold on user #{}: {}".format(user_id, reason[:150]),
        is_successful=True,
    )
    return record


def remove_legal_hold(admin, user_id: int) -> UserDeletion:
    """Lift a hold.

    The account returns to whichever state its own request implies: back into
    the grace period when a deletion request is still outstanding, otherwise
    simply active. It is never erased as a side effect of lifting a hold.
    """
    record = get_user_deletion(user_id)
    if record is None or record.status != DeletionStatus.LEGAL_HOLD:
        raise CustomValidationError("This user is not on legal hold.")

    had_pending_request = bool(record.requested_at and not record.cancelled_at)
    record.status = (
        DeletionStatus.IN_GRACE_PERIOD if had_pending_request else DeletionStatus.ACTIVE
    )
    if had_pending_request and not record.grace_period_ends_at:
        record.grace_period_ends_at = timezone.now() + timedelta(days=GRACE_PERIOD_DAYS)
    record.legal_hold_reason = ""
    record.legal_hold_by = None
    record.legal_hold_at = None
    record.save()

    log_audit_event(
        user=admin,
        action_type=ActionType.MODIFICATION,
        action_category="moderation",
        action_description="Removed legal hold on user #{}".format(user_id),
        is_successful=True,
    )
    return record


def _erase_own_content(user) -> Dict[str, int]:
    """Delete what belongs only to this user; anonymize what does not."""
    from testimonies.constants import SubmissionVisibility
    from testimonies.models import Highlight, Miracle, Testimony

    counts: Dict[str, int] = {}

    # Private submissions were never published and are the user's own, so they
    # go. Public and anonymous ones are ministry record: they stay, with the
    # author link cut and a public one demoted to anonymous so the UI cannot
    # imply a named author that no longer exists.
    for model, label in ((Testimony, "testimonies"), (Miracle, "miracles"), (Highlight, "highlights")):
        private = model.objects.filter(user=user, visibility=SubmissionVisibility.PRIVATE)
        counts["{}_deleted".format(label)] = private.count()
        private.delete()

        remaining = model.objects.filter(user=user)
        counts["{}_anonymized".format(label)] = remaining.count()
        remaining.update(user=None, visibility=SubmissionVisibility.ANONYMOUS)

    return counts


def _anonymize_shared_records(user) -> Dict[str, int]:
    """Cut the user out of records the organisation still needs."""
    from missions.models import MissionJIAParticipant
    from souls.models import ProgressUpdate, Soul

    counts: Dict[str, int] = {}

    # Souls and progress updates are the ministry's follow-up history and other
    # carers depend on them, so the rows stay and only the author link is cut.
    counts["souls_anonymized"] = Soul.objects.filter(user=user).update(user=None)
    counts["progress_updates_anonymized"] = ProgressUpdate.objects.filter(
        author=user
    ).update(author=None)

    # A registration carries its OWN copy of the registrant's name and phone,
    # so nulling the FK alone would not anonymize it. full_name keeps the row's
    # pk to stay unique under unique_together(mission, full_name, phone_number).
    registrations = MissionJIAParticipant.objects.filter(user=user)
    counts["registrations_anonymized"] = registrations.count()
    for registration in registrations:
        registration.user = None
        registration.full_name = "{} #{}".format(ANONYMIZED_NAME, registration.pk)
        registration.phone_number = PLACEHOLDER_PHONE
        registration.partner_name = ""
        registration.travelling_from = ""
        registration.diet_advisory = ""
        registration.save(update_fields=[
            "user", "full_name", "phone_number", "partner_name",
            "travelling_from", "diet_advisory", "updated_at",
        ])

    return counts


def _delete_private_account_data(user) -> Dict[str, int]:
    from authentication.models import PasswordResetToken, RefreshToken
    from notifications.models import Notification
    from personal_missions.models import PersonalMission
    from souls.models import SoulAssignment

    counts: Dict[str, int] = {}
    # PersonalMission.owner is PROTECT, so these must go before the user row is
    # touched; they are the user's own private plans and nobody else reads them.
    counts["personal_missions_deleted"] = PersonalMission.objects.filter(owner=user).count()
    PersonalMission.objects.filter(owner=user).delete()

    counts["notifications_deleted"] = Notification.objects.filter(user=user).count()
    Notification.objects.filter(user=user).delete()

    counts["soul_assignments_deleted"] = SoulAssignment.objects.filter(user=user).count()
    SoulAssignment.objects.filter(user=user).delete()

    RefreshToken.objects.filter(user=user).delete()
    PasswordResetToken.objects.filter(user=user).delete()

    # Their own reports stay so the queue keeps its history, but unattributed.
    ContentReport.objects.filter(reporter=user).update(reporter=None)
    return counts


def _scrub_user_row(user) -> None:
    """Overwrite every identifying column on the account itself.

    The User row is scrubbed rather than deleted because ``AuditLog.user`` is
    PROTECT and the audit trail has its own retention requirement: a real
    DELETE would either raise or take the audit history with it. After this
    runs the row holds no personal data, which is the outcome erasure requires,
    while the audit entries that reference it stay intact and attributable to
    an account id.
    """
    user.first_name = ANONYMIZED_NAME
    user.last_name = ""
    user.preferred_username = None
    user.email = "deleted-user-{}@deleted.invalid".format(user.pk)
    user.username = "deleted-user-{}".format(user.pk)
    user.phone_number = None
    user.church = None
    user.bio = None
    user.gender = None
    user.travelling_from = None
    user.diet_advisory = None
    user.emergency_contact_name = None
    user.emergency_contact_phone = None
    user.emergency_contact_confirmed_at = None
    user.saved_partner = None
    if user.profile_photo:
        user.profile_photo.delete(save=False)
    user.profile_photo = None
    user.is_active = False
    user.set_unusable_password()
    user.save()
    user.roles.clear()


@transaction.atomic
def perform_erasure(user_deletion: UserDeletion, actor=None) -> UserDeletion:
    """Carry out erasure for one account.

    Refuses while a legal hold stands or the grace period is still running, so
    neither the scheduled job nor a manual call can erase an account early.
    """
    user = user_deletion.user
    now = timezone.now()

    if user_deletion.status == DeletionStatus.LEGAL_HOLD:
        raise ForbiddenError("This account is on legal hold and cannot be erased.")
    if user_deletion.status == DeletionStatus.ERASURE_COMPLETE:
        return user_deletion
    if user_deletion.grace_period_ends_at and user_deletion.grace_period_ends_at > now:
        raise ForbiddenError(
            "The grace period for this account runs until {}.".format(
                user_deletion.grace_period_ends_at.isoformat()
            )
        )

    user_deletion.status = DeletionStatus.ERASURE_IN_PROGRESS
    user_deletion.save(update_fields=["status", "updated_at"])

    counts: Dict[str, int] = {}
    counts.update(_erase_own_content(user))
    counts.update(_anonymize_shared_records(user))
    counts.update(_delete_private_account_data(user))
    _scrub_user_row(user)

    user_deletion.status = DeletionStatus.ERASURE_COMPLETE
    user_deletion.completed_at = now
    user_deletion.save(update_fields=["status", "completed_at", "updated_at"])

    log_audit_event(
        user=actor or user,
        action_type=ActionType.DELETION,
        action_category="moderation",
        action_description="Erased account #{} ({})".format(
            user.pk,
            ", ".join("{}={}".format(k, v) for k, v in sorted(counts.items())),
        ),
        is_successful=True,
    )
    logger.info("Erasure complete for user %s: %s", user.pk, counts)
    return user_deletion
