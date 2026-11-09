"""Schemas Pydantic de voz."""
from typing import Optional

from pydantic import BaseModel, Field


class VoiceInfo(BaseModel):
    id: str
    name: str
    language: str
    quality: str
    gender: Optional[str] = None


class VoiceListResponse(BaseModel):
    available: bool
    provider: str
    voices: list[VoiceInfo]


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice_id: Optional[str] = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class SynthesizeResponse(BaseModel):
    audio_path: str
    audio_url: str
    voice_id: str
    duration: Optional[float]
    size_bytes: int