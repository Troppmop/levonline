from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep, require_roles
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.enums import UserRole
from app.schemas.auth import (
    PasswordChange,
    ProfileUpdate,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.login_rate_limit)
async def login(request: Request, session: SessionDep, form_data: OAuth2PasswordRequestForm = Depends()):
    service = AuthService(session)
    user = await service.authenticate(form_data.username, form_data.password)
    return await service.issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(settings.refresh_rate_limit)
async def refresh(request: Request, session: SessionDep, payload: RefreshRequest):
    service = AuthService(session)
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=204)
async def logout(session: SessionDep, payload: RefreshRequest):
    service = AuthService(session)
    await service.logout(payload.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUser):
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(session: SessionDep, current_user: CurrentUser, payload: ProfileUpdate):
    service = AuthService(session)
    return await service.update_profile(current_user, payload)


@router.post("/me/change-password", status_code=204)
async def change_my_password(session: SessionDep, current_user: CurrentUser, payload: PasswordChange):
    """Revokes every other refresh token on success — see AuthService for why."""
    service = AuthService(session)
    await service.change_password(current_user, payload)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def register(session: SessionDep, payload: UserCreate):
    """Admin-only: create staff / Av-Bayit accounts."""
    service = AuthService(session)
    return await service.register_user(payload)
