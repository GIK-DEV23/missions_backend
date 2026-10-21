from typing import List

from ninja import Router

from authentication.permissions import jwt_auth
from authentication.decorators import require_permission
from base.schemas import DetailOut
from personal_missions import schemas, services, selectors

router = Router(tags=["personal_missions"])


@router.get(
    "/",
    response={200: List[schemas.PersonalMissionOut]},
    auth=jwt_auth
)
@require_permission("list_personal_missions")
def personal_missions_list_api(request):
    """Owner-scoped list of the caller's own personal missions (excludes archived)."""
    personal_missions = selectors.list_personal_missions_with_rhythm(user=request.user, include_archived=False)
    return personal_missions


@router.get(
    "/archived/",
    response={200: List[schemas.PersonalMissionOut]},
    auth=jwt_auth
)
@require_permission("list_personal_missions")
def archived_personal_missions_list_api(request):
    """Owner-scoped list of the caller's archived personal missions only."""
    archived_missions = selectors.list_archived_personal_missions_with_rhythm(user=request.user)
    return archived_missions


@router.post(
    "/",
    response={201: schemas.PersonalMissionOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("create_personal_mission")
def create_personal_mission_api(request, personal_mission_in: schemas.PersonalMissionCreate):
    personal_mission = services.create_personal_mission(owner=request.user, data=personal_mission_in.dict())
    return 201, selectors.serialize_mission_with_rhythm(personal_mission)


@router.patch(
    "/{personal_mission_id}/",
    response={200: schemas.PersonalMissionOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("update_personal_mission")
def update_personal_mission_api(request, personal_mission_id: int, personal_mission_in: schemas.PersonalMissionUpdate):
    personal_mission = services.update_personal_mission(
        user=request.user,
        personal_mission_id=personal_mission_id,
        data=personal_mission_in.dict(exclude_unset=True)
    )
    return 200, selectors.serialize_mission_with_rhythm(personal_mission)


@router.post(
    "/{personal_mission_id}/archive/",
    response={200: schemas.PersonalMissionOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("archive_personal_mission")
def archive_personal_mission_api(request, personal_mission_id: int):
    personal_mission = services.archive_personal_mission(user=request.user, personal_mission_id=personal_mission_id)
    return 200, selectors.serialize_mission_with_rhythm(personal_mission)


# ─── Session Endpoints ─────────────────────────────────────────────────────────

@router.post(
    "/{personal_mission_id}/sessions/",
    response={201: schemas.SessionOut, 400: DetailOut},
    auth=jwt_auth
)
@require_permission("create_personal_mission")  # Same permission as creating missions
def create_session_api(request, personal_mission_id: int, session_in: schemas.SessionCreate):
    """
    Log a session for a personal mission.
    
    This marks the rhythm period containing the session date as 'met'.
    Use this when conducting the mission without adding new souls or check-ins.
    """
    session = services.create_session(
        user=request.user,
        mission_id=personal_mission_id,
        data=session_in.dict()
    )
    return 201, schemas.SessionOut(**session.to_dict(request))


@router.get(
    "/{personal_mission_id}/sessions/",
    response={200: List[schemas.SessionOut]},
    auth=jwt_auth
)
@require_permission("list_personal_missions")
def list_sessions_api(request, personal_mission_id: int):
    """List all sessions for a personal mission."""
    sessions = selectors.list_sessions(user=request.user, mission_id=personal_mission_id)
    return [schemas.SessionOut(**s.to_dict(request)) for s in sessions]
