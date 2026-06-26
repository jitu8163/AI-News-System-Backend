"""First-run database seeding.

Runs automatically on application startup (see main.py lifespan). The admin
seed is idempotent: the admin user is created from the configured credentials
only when it does not already exist. If the admin is already present, its
password and flags are left untouched — so an operator who later changes the
password through the UI will not have it reset on the next deploy/restart.
"""
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def seed_admin_if_missing() -> None:
    """Create the initial admin user if no user with ADMIN_EMAIL exists."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        if result.scalar_one_or_none() is not None:
            logger.info("admin_seed_skipped", email=settings.ADMIN_EMAIL)
            return

        session.add(
            User(
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                is_admin=True,
                is_active=True,
            )
        )
        await session.commit()
        logger.info("admin_seeded", email=settings.ADMIN_EMAIL)
