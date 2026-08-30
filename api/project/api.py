from typing import Union

from django.http import HttpRequest, HttpResponse, JsonResponse
from ninja import NinjaAPI
from pydantic import ValidationError

from authentication.api import router as auth_router
from audit_logs.api import router as audit_logs_router
from users.api import router as users_router, me_router
from missions.api import router as missions_router, registrations_router
from souls.api import router as souls_router
from testimonies.api import router as testimonies_router, highlight_router
from sync.api import router as sync_router
from personal_missions.api import router as personal_missions_router
from notifications.api import router as notifications_router


api = NinjaAPI()


@api.get("/health/")
def health_check(request: HttpRequest):
    return JsonResponse({"status": "ok"})

api.add_router("audit_logs/", audit_logs_router)
api.add_router("/auth/", auth_router)
api.add_router("/users/", users_router)
api.add_router("/me/", me_router)
api.add_router("/missions/", missions_router)
api.add_router("/registrations/", registrations_router)
api.add_router("/souls/", souls_router)
api.add_router("/testimonies/", testimonies_router)
api.add_router("/highlights/", highlight_router)
api.add_router("/sync/", sync_router)
api.add_router("/personal-missions/", personal_missions_router)
api.add_router("/notifications/", notifications_router)


@api.exception_handler(ValidationError)
def validation_errors(request: HttpRequest, exc: Union[ValidationError, str]) -> HttpResponse:
    """Customize validation error"""
    if isinstance(exc, str):
        response = {"detail": exc}
    else:
        response = {"detail": exc.errors}

    return api.create_response(request, response, status=400)
