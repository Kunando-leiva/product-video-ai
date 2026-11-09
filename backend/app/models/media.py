"""Schemas Pydantic de Media."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict  # pyright: ignore[reportMissingImports]


class MediaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    type: str
    filename: str
    original_name: str
    path: str
    url: str  # ruta HTTP para servirlo (calculada en el service)
    duration: Optional[float]
    width: Optional[int]
    height: Optional[int]
    fps: Optional[float]
    orientation: Optional[str]
    thumbnail_path: Optional[str]
    thumbnail_url: Optional[str]
    created_at: datetime