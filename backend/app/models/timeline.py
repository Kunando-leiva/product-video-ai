"""Schemas Pydantic de TimelineItem."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TimelineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    media_id: Optional[str] = None
    order_index: int
    start: float
    duration: float
    effect: Optional[str] = None
    text: Optional[str] = None


class TimelineItemWrite(BaseModel):
    """Lo que manda el frontend (sin id ni project_id, se generan)."""

    media_id: Optional[str] = None
    duration: float = Field(default=3.0, gt=0, le=600)
    effect: Optional[str] = None
    start: float = 0.0
    text: Optional[str] = None


class TimelineReplaceRequest(BaseModel):
    items: list[TimelineItemWrite]


class TimelineRead(BaseModel):
    items: list[TimelineItemRead]