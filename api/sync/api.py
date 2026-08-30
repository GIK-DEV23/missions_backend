from ninja import Router, Query

from authentication.permissions import jwt_auth
from authentication.decorators import require_permission
from base.schemas import DetailOut
from base.utils.exceptions import CustomValidationError
from sync import schemas, services, selectors

router = Router(tags=["sync"])

MAX_MUTATIONS_PER_BATCH = 500


@router.post(
    "mutations/",
    response={200: schemas.MutationsOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("sync_mutations")
def sync_mutations_api(request, body: schemas.MutationsIn):
    if len(body.mutations) > MAX_MUTATIONS_PER_BATCH:
        raise CustomValidationError(
            "Too many mutations in one batch (max {}).".format(MAX_MUTATIONS_PER_BATCH)
        )
    results = services.apply_mutations(request.user, [m.dict() for m in body.mutations])
    return 200, {"results": results}


@router.get(
    "changes/",
    response={200: dict, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("sync_changes")
def sync_changes_api(request, params: schemas.ChangesQuery = Query(...)):
    return 200, selectors.changes_since(request.user, params.since, request=request)
