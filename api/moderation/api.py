"""Moderation endpoints.

Paths match what missions-web-admin's `moderation.service.ts` already calls, so
the dashboard's shipped Moderation page works against this without edits:

    GET    /moderation/reports/
    POST   /moderation/reports/
    POST   /moderation/reports/bulk-update/
    GET    /moderation/reports/{id}/
    PATCH  /moderation/reports/{id}/
    GET    /moderation/stats/

Trailing slashes are deliberate and match every other router here; mobile is
being aligned to them rather than the reverse (BR-1b).

NOTE ON DECORATOR ORDER: @router.<method> must stay OUTERMOST, with
@require_permission beneath it. django-ninja registers the function it is
handed and returns it unchanged, so a permission decorator placed above the
route decorator is never applied — that silently unguarded 27 endpoints across
three routers before it was fixed.
"""

from django.http import JsonResponse
from ninja import Query, Router

from authentication.decorators import require_permission
from authentication.permissions import jwt_auth
from base.api import paginate_response
from base.schemas import DetailOut
from moderation import schemas, selectors, services

router = Router(tags=["moderation"])


@router.get(
    "/reports/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth,
)
@require_permission("list_content_reports")
def reports_list_api(request, params: schemas.ReportsQuery = Query(...)):
    """Review queue. Each row carries a preview of the reported content."""
    reports = selectors.list_reports(
        filters=params.dict(exclude={"page", "page_size"})
    )
    response = paginate_response(
        queryset=reports,
        request=request,
        schema=schemas.ContentReportOut,
        page=params.page,
        page_size=params.page_size,
        to_dict_kwargs={"include_preview": True},
    )
    return JsonResponse(response, safe=False)


@router.post(
    "/reports/",
    response={201: schemas.ContentReportOut, 400: DetailOut},
    auth=jwt_auth,
)
@require_permission("create_content_report")
def create_report_api(request, report_in: schemas.ContentReportCreate):
    """Report a piece of content.

    Idempotent by client_id, so a report queued offline on mobile and retried
    is recorded once.
    """
    report = services.create_report(reporter=request.user, data=report_in.dict())
    return 201, schemas.ContentReportOut(**report.to_dict(request, include_preview=True))


@router.post(
    "/reports/bulk-update/",
    response={200: schemas.BulkUpdateOut, 400: DetailOut},
    auth=jwt_auth,
)
@require_permission("review_content_report")
def bulk_update_reports_api(request, body: schemas.ContentReportBulkUpdate):
    """Apply one decision to several reports.

    Reports the decision cannot apply to are returned in `skipped` rather than
    failing the batch.
    """
    payload = body.dict()
    ids = payload.pop("ids")
    result = services.bulk_update_reports(reviewer=request.user, ids=ids, data=payload)
    return 200, schemas.BulkUpdateOut(**result)


@router.get(
    "/reports/mine/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth,
)
@require_permission("create_content_report")
def my_reports_list_api(request, params: schemas.ReportsQuery = Query(...)):
    """The caller's OWN reports.

    Gated on `create_content_report`, not `list_content_reports`: anyone who
    can file a report may see what happened to theirs, while the review queue
    at GET /reports/ stays restricted to reviewers. Owner-scoped, so it never
    exposes another reporter's submissions.

    No content preview — a reporter should not be handed back an excerpt of
    content a reviewer may since have removed.
    """
    reports = selectors.list_reports_by_reporter(request.user)
    response = paginate_response(
        queryset=reports,
        request=request,
        schema=schemas.ContentReportOut,
        page=params.page,
        page_size=params.page_size,
    )
    return JsonResponse(response, safe=False)


@router.get(
    "/reports/{report_id}/",
    response={200: schemas.ContentReportOut, 404: DetailOut},
    auth=jwt_auth,
)
@require_permission("view_content_report")
def report_details_api(request, report_id: int):
    report = selectors.get_report(report_id)
    return 200, schemas.ContentReportOut(**report.to_dict(request, include_preview=True))


@router.patch(
    "/reports/{report_id}/",
    response={200: schemas.ContentReportOut, 400: DetailOut, 404: DetailOut},
    auth=jwt_auth,
)
@require_permission("review_content_report")
def update_report_api(request, report_id: int, report_in: schemas.ContentReportUpdate):
    """Record a review decision.

    `resolved_removed` is only valid for a testimony or miracle; a soul or user
    report must close as resolved_no_action or dismissed with a note.
    """
    report = services.update_report(
        reviewer=request.user,
        report_id=report_id,
        data=report_in.dict(exclude_unset=True),
    )
    return 200, schemas.ContentReportOut(**report.to_dict(request, include_preview=True))


@router.get(
    "/stats/",
    response={200: schemas.ModerationStatsOut},
    auth=jwt_auth,
)
@require_permission("view_moderation_stats")
def moderation_stats_api(request):
    return 200, schemas.ModerationStatsOut(**selectors.moderation_stats())
