from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)

    async def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate user and return JWT token.

        Raises ValueError on bad credentials.
        """
        user = await self._repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is disabled")

        token = create_access_token(subject=user.id)
        logger.info("user_login", user_id=user.id, email=email)
        return TokenResponse(access_token=token)

    async def get_user_by_id(self, user_id: int):
        """Return user or None."""
        return await self._repo.get(user_id)

    async def change_password(self, user_id: int, current_password: str, new_password: str) -> None:
        """Change password. Raises ValueError on wrong current password."""
        user = await self._repo.get(user_id)
        if not user or not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")
        user.hashed_password = hash_password(new_password)
        await self._session.commit()
        logger.info("password_changed", user_id=user_id)
