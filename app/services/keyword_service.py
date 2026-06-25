from sqlalchemy.ext.asyncio import AsyncSession

from app.models.keyword import Keyword
from app.repositories.keyword_repository import KeywordRepository
from app.schemas.keyword import KeywordCreate, KeywordUpdate
from app.utils.logging import get_logger

logger = get_logger(__name__)


class KeywordService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = KeywordRepository(session)

    async def list_keywords(self) -> list[Keyword]:
        return await self._repo.list_all()

    async def create_keyword(self, data: KeywordCreate) -> Keyword:
        existing = await self._repo.get_by_term(data.term)
        if existing:
            raise ValueError(f"Keyword '{data.term}' already exists")
        keyword = await self._repo.create(term=data.term)
        logger.info("keyword_created", term=data.term)
        return keyword

    async def update_keyword(self, keyword_id: int, data: KeywordUpdate) -> Keyword:
        keyword = await self._repo.get(keyword_id)
        if not keyword:
            raise LookupError(f"Keyword {keyword_id} not found")

        updates = data.model_dump(exclude_unset=True)
        if "term" in updates:
            duplicate = await self._repo.get_by_term(updates["term"])
            if duplicate and duplicate.id != keyword_id:
                raise ValueError(f"Keyword '{updates['term']}' already exists")

        updated = await self._repo.update(keyword, **updates)
        logger.info("keyword_updated", keyword_id=keyword_id, updates=updates)
        return updated

    async def delete_keyword(self, keyword_id: int) -> None:
        keyword = await self._repo.get(keyword_id)
        if not keyword:
            raise LookupError(f"Keyword {keyword_id} not found")
        await self._repo.delete(keyword)
        logger.info("keyword_deleted", keyword_id=keyword_id)

    async def set_active(self, keyword_id: int, active: bool) -> Keyword:
        keyword = await self._repo.get(keyword_id)
        if not keyword:
            raise LookupError(f"Keyword {keyword_id} not found")
        return await self._repo.update(keyword, is_active=active)
