from typing import List

from ninja import Router

from authentication.permissions import jwt_auth
from authentication.decorators import require_permission
from base.schemas import DetailOut
from personal_missions import schemas, services, selectors

router = Router(tags=["personal_missions"])


@require_permission("list_personal_missions")
@router.get(
    "/",
    response={200: List[schemas.PersonalMissionOut]},
    auth=jwt_auth
)
def personal_missions_list_api(request):
    """Owner-scoped list of the caller's own personal missions."""
    personal_missions = selectors.list_personal_missions(user=request.user)
    return [schemas.PersonalMissionOut(**pm.to_dict(request)) for pm in personal_missions]


@require_permission("create_personal_mission")
@router.post(
    "/",
    response={201: schemas.PersonalMissionOut, 400: DetailOut},
    auth=jwt_auth
)
def create_personal_mission_api(request, personal_mission_in: schemas.PersonalMissionCreate):
    personal_mission = services.create_personal_mission(owner=request.user, data=personal_mission_in.dict())
    return 201, schemas.PersonalMissionOut(**personal_mission.to_dict(request))


@require_permission("update_personal_mission")
@router.patch(
    "/{personal_mission_id}/",
    response={200: schemas.PersonalMissionOut, 400: DetailOut},
    auth=jwt_auth
)
def update_personal_mission_api(request, personal_mission_id: int, personal_mission_in: schemas.PersonalMissionUpdate):
    personal_mission = services.update_personal_mission(
        user=request.user,
        personal_mission_id=personal_mission_id,
        data=personal_mission_in.dict(exclude_unset=True)
    )
    return 200, schemas.PersonalMissionOut(**personal_mission.to_dict(request))


@require_permission("archive_personal_mission")
@router.post(
    "/{personal_mission_id}/archive/",
    response={200: schemas.PersonalMissionOut, 400: DetailOut},
    auth=jwt_auth
)
def archive_personal_mission_api(request, personal_mission_id: int):
    personal_mission = services.archive_personal_mission(user=request.user, personal_mission_id=personal_mission_id)
    return 200, schemas.PersonalMissionOut(**personal_mission.to_dict(request))
