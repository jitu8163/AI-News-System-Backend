from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword import Keyword
from app.repositories.base import BaseRepository


class KeywordRepository(BaseRepository[Keyword]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Keyword, session)

    async def get_by_term(self, term: str) -> Keyword | None:
        result = await self._session.execute(select(Keyword).where(Keyword.term == term))
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Keyword]:
        result = await self._session.execute(
            select(Keyword).where(Keyword.is_active.is_(True)).order_by(Keyword.term)
        )
        return list(result.scalars().all())

    async def list_all(self, offset: int = 0, limit: int = 100) -> list[Keyword]:
        result = await self._session.execute(
            select(Keyword).order_by(Keyword.term).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, keyword: Keyword, **kwargs) -> Keyword:
        for key, value in kwargs.items():
            setattr(keyword, key, value)
        await self._session.flush()
        await self._session.refresh(keyword)
        return keyword
