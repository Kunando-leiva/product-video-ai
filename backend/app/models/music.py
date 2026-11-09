"""Schemas Pydantic de música."""
from typing import Optional

from pydantic import BaseModel, Field


class MusicTrackInfo(BaseModel):
    id: str
    name: str
    filename: str
    duration: Optional[float]
    size_bytes: int
    url: Optional[str] = None


class MusicListResponse(BaseModel):
    tracks: list[MusicTrackInfo]


class MusicSelectionRequest(BaseModel):
    """Actualiza la selección de música + voz del proyecto."""
    music_enabled: Optional[bool] = None
    music_track: Optional[str] = None
    music_volume: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    voice_track: Optional[str] = None
    voice_enabled: Optional[bool] = None


class MusicSelectionResponse(BaseModel):
    music_enabled: bool
    music_track: Optional[str]
    music_volume: float
    voice_enabled: bool
    voice_track: Optional[str]