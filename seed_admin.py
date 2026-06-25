"""
Seed (or reset) the initial admin user.

Run from the backend directory:
    uv run python seed_admin.py                       # use defaults below
    uv run python seed_admin.py admin@site.com Secret  # custom email/password

Idempotent: if the admin already exists, its password is reset to the value
given here, so this is also the way to recover a lost/changed admin password.
Requires the database schema to exist first (`alembic upgrade head`).
"""
import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Initial admin credentials. Change these (or pass them as CLI args) before
# deploying to production.
DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "Admin@123"


async def seed_admin(email: str, password: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            session.add(
                User(
                    email=email,
                    hashed_password=hash_password(password),
                    is_admin=True,
                    is_active=True,
                )
            )
            action = "created"
        else:
            user.hashed_password = hash_password(password)
            user.is_admin = True
            user.is_active = True
            action = "password reset"

        await session.commit()

    print(f"Admin {action}: {email}")
    print("You can now log in with the credentials above.")


def main() -> None:
    email = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADMIN_EMAIL
    password = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_ADMIN_PASSWORD
    asyncio.run(seed_admin(email, password))


if __name__ == "__main__":
    main()
