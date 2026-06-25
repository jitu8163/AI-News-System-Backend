from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.keyword import KeywordCreate, KeywordResponse, KeywordUpdate
from app.services.keyword_service import KeywordService

router = APIRouter(prefix="/keywords", tags=["keywords"])


def _svc(session: AsyncSession = Depends(get_db)) -> KeywordService:
    return KeywordService(session)


@router.get("", response_model=list[KeywordResponse])
async def list_keywords(
    svc: KeywordService = Depends(_svc),
) -> list[KeywordResponse]:
    """List all keywords (public — used to populate filters)."""
    return await svc.list_keywords()


@router.post("", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
async def create_keyword(
    data: KeywordCreate,
    svc: KeywordService = Depends(_svc),
    _: User = Depends(get_current_admin),
) -> KeywordResponse:
    """Create a new monitoring keyword."""
    try:
        keyword = await svc.create_keyword(data)
        return KeywordResponse.model_validate(keyword)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.put("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: int,
    data: KeywordUpdate,
    svc: KeywordService = Depends(_svc),
    _: User = Depends(get_current_admin),
) -> KeywordResponse:
    """Update keyword term or active state."""
    try:
        keyword = await svc.update_keyword(keyword_id, data)
        return KeywordResponse.model_validate(keyword)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: int,
    svc: KeywordService = Depends(_svc),
    _: User = Depends(get_current_admin),
) -> None:
    """Delete a keyword."""
    try:
        await svc.delete_keyword(keyword_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
