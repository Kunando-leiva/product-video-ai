"""Schemas Pydantic de Project."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


FORMATS = ("9:16", "1:1", "4:5", "16:9")
DURATIONS = (30, 60, 90, 120)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    product_url: str = Field("", max_length=2000)
    format: str = Field("9:16")
    duration: int = Field(30)

    def validate_enum(self) -> None:
        if self.format not in FORMATS:
            raise ValueError(f"format debe ser uno de {FORMATS}")
        if self.duration not in DURATIONS:
            raise ValueError(f"duration debe ser uno de {DURATIONS}")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    product_name: Optional[str] = Field(None, max_length=200)
    product_description: Optional[str] = None
    product_url: Optional[str] = Field(None, max_length=2000)
    duration: Optional[int] = None
    format: Optional[str] = None
    style: Optional[str] = None
    voice_enabled: Optional[bool] = None
    voice_provider: Optional[str] = None
    voice_name: Optional[str] = None
    subtitles_enabled: Optional[bool] = None
    subtitles_style: Optional[str] = None
    music_enabled: Optional[bool] = None
    music_track: Optional[str] = None
    music_volume: Optional[float] = None
    script_json: Optional[dict] = None
    timeline_json: Optional[list] = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    product_name: str
    product_description: str
    product_url: str
    duration: int
    format: str
    style: str
    voice_enabled: bool
    voice_provider: str
    voice_name: str
    subtitles_enabled: bool
    subtitles_style: str
    music_enabled: bool
    music_track: Optional[str]
    music_volume: float
    created_at: datetime
    updated_at: datetime