import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import decode_token
from app.models.enums import UserRole
from app.models.resident import Resident
from app.models.user import User
from app.repositories.resident_repository import ResidentRepository
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_error
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except jwt.PyJWTError as exc:
        raise credentials_error from exc

    user = await UserRepository(session).get(uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return checker


# Building operations (residents, rooms, inventory, maintenance) are staff
# business, not something an Av/Eim Bayit account — scoped to meal hosting
# reports — should be able to touch.
StaffOrAdmin = Annotated[User, Depends(require_roles(UserRole.STAFF, UserRole.ADMIN))]

# Bulk data import/export and account creation: admin-only, not staff — this
# is whole-database-shaped access (every table, including other staff's
# accounts), a materially bigger blast radius than day-to-day building ops.
AdminOnly = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


async def get_non_resident_user(user: CurrentUser) -> User:
    """Gate for endpoints that browse across residents (roster lists, the
    presence board, etc.). Staff/admin/av_bayit all have legitimate reasons
    to see the whole roster; a resident account should only ever see itself,
    via the /residents/me routes."""
    if user.role == UserRole.RESIDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resident accounts can only access their own profile",
        )
    return user


NotResident = Annotated[User, Depends(get_non_resident_user)]


async def get_current_resident(session: SessionDep, user: CurrentUser) -> Resident:
    """Resolves the Resident profile linked to a RESIDENT-role login, for
    the resident's own self-service endpoints (status toggle, RSVPs, filing
    a report). 403s for any non-resident role or an unlinked account."""
    if user.role != UserRole.RESIDENT or user.resident_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available to resident accounts",
        )
    resident = await ResidentRepository(session).get_with_room(user.resident_id)
    if resident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked resident profile not found")
    return resident


CurrentResident = Annotated[Resident, Depends(get_current_resident)]
