"""
Authentication API endpoints using Django Ninja.
"""
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router, Form
from ninja.errors import HttpError

from audit_logs.services import log_audit_event
from authentication.backends import get_backend
from authentication.permissions import jwt_auth
from authentication.schemas import (
    AuthProviderListResponse,
    AuthResponse,
    LoginRequest,
    SocialAuthRequest,
    SocialAuthResponse,
    TokenVerificationResponse, TokenRefreshIn,
    UserData, ManualRegisterRequest,
    RequestPasswordResetIn, ResetPasswordIn
)
from authentication.utils import get_auth_for_user, authenticate_social_user
from authentication import services as auth_services
from base.schemas import DetailOut
from users import services as user_services
from users.models import AuthProvider, User

router = Router(tags=["auth"])


def _client_ip(request: HttpRequest) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _rate_limited(cache_key: str, max_attempts: int, window_seconds: int) -> bool:
    count = cache.get(cache_key, 0)
    if count >= max_attempts:
        return True
    cache.set(cache_key, count + 1, timeout=window_seconds)
    return False


@router.post(
    "/login",
    response={200: AuthResponse, 400: DetailOut, 401: DetailOut, 403: DetailOut}
)
def login(request, data: LoginRequest):
    """
    Traditional email/password login endpoint.

    Authenticates a user with email and password, returning tokens on success.
    """
    email = data.email
    password = data.password

    # Authenticate using Django's built-in system
    user = authenticate(email=email, password=password)

    current_time = timezone.now()
    # Format current time as 'YYYY-MM-DD HH:MM:SS'
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    if not user:
        raise HttpError(401, "Invalid email or password")

    if not user.is_active:
        raise HttpError(403, "User account is disabled")

    # Generate authentication data
    auth_data = get_auth_for_user(user)

    if not user.is_staff:
        return auth_data

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    existing_ip = cache.get("user_ip_{}".format(user.id))
    if existing_ip != ip_address:
        cache.set("user_ip_{}".format(user.id), ip_address, timeout=604800)
    log_audit_event(
        user=user,
        action_type="login",
        action_category="authentication",
        action_description="{} logged in via email/password at {} using IP: {}".format(user.email if user else "Unknown user", formatted_time, ip_address),
        is_successful=bool(user),
        ip_address=ip_address
    )

    return auth_data


@router.post(
    "/manual_register",
    response={200: UserData, 400: DetailOut},
)
def manual_registration_api(request, user_in: ManualRegisterRequest = Form(...)):
    profile_photo = request.FILES.get("profile_photo")
    user = user_services.register_missioner(
        profile_photo=profile_photo,
        **user_in.dict(exclude=["profile_photo"])
    )
    return UserData(**user.to_dict(request))


@router.post(
    "/social",
    response={200: SocialAuthResponse, 400: DetailOut, 401: DetailOut}
)
def social_auth(request, data: SocialAuthRequest):
    """
    Social authentication endpoint.

    Authenticates with a social provider (Google or Apple).
    Accepts either a token or authorization code.
    """
    provider_name = data.provider
    token = data.token
    code = data.code
    user_data = data.user  # For Apple's initial auth with name data

    if not provider_name or (not token and not code):
        raise HttpError(400, "Provider name and token/code are required")

    # Get the appropriate backend
    backend = get_backend(provider_name)
    if not backend:
        raise HttpError(400, f"Provider {provider_name} not supported")

    # Authenticate with the provider
    auth_kwargs = {'user': user_data} if user_data else {}
    if token:
        auth_kwargs['access_token' if provider_name == 'google' else 'id_token'] = token
    elif code:
        auth_kwargs['code'] = code

    success, user_info, error = backend.authenticate(request, **auth_kwargs)

    if not success:
        raise HttpError(401, error or "Authentication failed")

    provider_user_id = user_info.get('provider_user_id')
    email = user_info.get('email')
    provider_data = user_info.get('provider_data', {})

    if not provider_user_id or not email:
        raise HttpError(400, "Provider did not return required user information")

    # Get or create user
    user, created = authenticate_social_user(
        provider_name,
        provider_user_id,
        email,
        provider_data
    )

    # Generate authentication data
    auth_data = get_auth_for_user(user)
    response_data = {**auth_data, "is_new_user": created}

    return response_data


@router.post(
    "/refresh",
    response={200: AuthResponse, 400: DetailOut},
    auth=jwt_auth
)
def refresh_token(request, data: TokenRefreshIn):
    """
    Token refresh endpoint.

    Expects an access token in the request body.
    Validates the token and returns a new one with refreshed expiration.
    """
    jwt_backend = get_backend('jwt')
    if not jwt_backend:
        raise HttpError(500, "JWT backend not available")

    try:
        payload = jwt_backend.decode_token(data.access_token)
    except Exception:
        raise HttpError(401, "Invalid or expired token")

    user_id = payload.get("user_id") or payload.get("id")
    if not user_id:
        raise HttpError(401, "Invalid token payload")

    user = User.objects.filter(id=user_id).first()
    if not user:
        raise HttpError(401, "User not found or token invalid")

    auth_data = get_auth_for_user(user)
    return auth_data



@router.get(
    "/verify",
    response=TokenVerificationResponse,
    auth=jwt_auth
)
def verify_token(request):
    """
    Token verification endpoint.

    Verifies the token in the Authorization header and returns user info if valid.
    """
    user = request.user

    if not user or not user.is_authenticated:
        return {"valid": False}

    return {
        "valid": True,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.get_display_name(),
            "is_superuser": user.is_superuser,
            "is_staff": user.is_staff,
            "auth_provider": getattr(
                user.get_primary_auth_provider(),
                'provider.name',
                'local'
            ) if hasattr(user, 'get_primary_auth_provider') else 'local',
            "roles": list(user.roles.values_list('name', flat=True)) if hasattr(user, 'roles') else []
        }
    }


@router.get("/providers", response=AuthProviderListResponse)
def auth_providers(request):
    """
    Get information about available authentication providers.
    """
    providers_data = []
    for provider in AuthProvider.objects.filter(is_active=True):
        auth_backend = get_backend(provider.name)
        auth_url = None

        if auth_backend:
            try:
                auth_url = auth_backend.get_auth_url()
            except NotImplementedError:
                pass

        providers_data.append({
            "name": provider.name,
            "display_name": provider.display_name,
            "supports_registration": provider.allow_registration,
            "auth_url": auth_url,
            "priority": provider.priority
        })

    return {"providers": providers_data}


@router.post(
    "/request-password-reset",
    response={200: DetailOut, 429: DetailOut},
)
def request_password_reset_api(request, data: RequestPasswordResetIn):
    """
    Always returns success whether or not the email exists — never reveal
    account existence through this endpoint.
    """
    ip = _client_ip(request)
    if _rate_limited("pwreset_email_{}".format(data.email.lower()), max_attempts=5, window_seconds=3600) or \
       _rate_limited("pwreset_ip_{}".format(ip), max_attempts=20, window_seconds=3600):
        raise HttpError(429, "Too many requests. Please try again later.")

    auth_services.request_password_reset(data.email)
    return 200, {"detail": "If that email exists, a reset link has been sent."}


@router.post(
    "/reset-password",
    response={200: DetailOut, 400: DetailOut, 429: DetailOut},
)
def reset_password_api(request, data: ResetPasswordIn):
    ip = _client_ip(request)
    if _rate_limited("pwreset_attempt_ip_{}".format(ip), max_attempts=20, window_seconds=3600):
        raise HttpError(429, "Too many requests. Please try again later.")

    auth_services.reset_password(data.token, data.new_password)
    return 200, {"detail": "Password reset successful."}

