"""One-off bootstrap: create the first admin user.

Run inside the backend container/venv:
    python -m app.scripts.seed_admin admin@lev.org "Admin Name" "strong-password"

Needed because the /auth/register endpoint requires an existing admin to
authorize new accounts — the very first admin has no one to authorize them.
"""
import asyncio
import sys

from app.core.db import session_scope
from app.core.exceptions import AuthError
from app.models.enums import UserRole
from app.schemas.auth import UserCreate
from app.services.auth_service import AuthService


async def main(email: str, full_name: str, password: str) -> None:
    async with session_scope() as session:
        service = AuthService(session)
        try:
            user = await service.register_user(
                UserCreate(email=email, password=password, full_name=full_name, role=UserRole.ADMIN)
            )
        except AuthError as exc:
            print(f"Could not create admin: {exc}")
            return
        print(f"Created admin user {user.email} ({user.id})")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print('Usage: python -m app.scripts.seed_admin <email> "<full name>" <password>')
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3]))
