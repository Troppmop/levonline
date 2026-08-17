import uuid

from fastapi import APIRouter, File, UploadFile

from app.api.deps import AdminOnly, SessionDep
from app.core.storage import save_avatar_photo
from app.schemas.auth import UserRead
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def list_users(session: SessionDep, _: AdminOnly):
    """Backs the admin's user picker for setting someone else's profile
    picture — not a general roster endpoint, so it's admin-only."""
    return await UserService(session).list_all()


@router.post("/{user_id}/avatar", response_model=UserRead)
async def upload_user_avatar(
    session: SessionDep, _: AdminOnly, user_id: uuid.UUID, file: UploadFile = File(...)
):
    url = await save_avatar_photo(user_id, file)
    return await UserService(session).set_avatar(user_id, url)
