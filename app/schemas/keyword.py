from datetime import datetime
from pydantic import BaseModel, field_validator


class KeywordCreate(BaseModel):
    term: str

    @field_validator("term")
    @classmethod
    def strip_term(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("term cannot be blank")
        return v


class KeywordUpdate(BaseModel):
    term: str | None = None
    is_active: bool | None = None

    @field_validator("term")
    @classmethod
    def strip_term(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("term cannot be blank")
        return v


class KeywordResponse(BaseModel):
    id: int
    term: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
