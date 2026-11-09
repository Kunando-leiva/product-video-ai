"""Schemas Pydantic de subtítulos."""
from typing import Optional

from pydantic import BaseModel, Field


class SegmentModel(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str = Field(min_length=1, max_length=500)


class TranscribeRequest(BaseModel):
    media_id: str
    language: Optional[str] = Field(default=None, max_length=8)
    model: str = Field(default="small", max_length=32)


class TranscribeResponse(BaseModel):
    segments: list[SegmentModel]
    srt: str
    language: Optional[str] = None


class SubtitleRead(BaseModel):
    exists: bool
    srt: Optional[str] = None
    segments: list[SegmentModel] = Field(default_factory=list)


class SubtitleUpdate(BaseModel):
    segments: list[SegmentModel]


class BurnRequest(BaseModel):
    render_job_id: Optional[str] = None  # si None, usa el último completed