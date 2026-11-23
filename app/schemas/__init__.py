from datetime import datetime
from uuid import UUID
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    post_id: UUID
    source_id: UUID
    source_type: str
    url: str
    title: str | None
    text: str
    published_at: datetime
    collected_at: datetime
    language: str
    processing_status: str
    is_deleted_at_source: bool
    updated_at: datetime
    topics: list[dict[str, Any]] = []
    regions: list[dict[str, Any]] = []
    sentiment: list[dict[str, Any]] = []


class Page(BaseModel):
    items: list[PostOut]
    total: int
    offset: int
    limit: int


class Correction(BaseModel):
    object_type: Literal['topic', 'region']
    label: str
    accepted: bool = True
    reason: str = Field(min_length=5, max_length=2000)
