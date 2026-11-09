"""Schemas Pydantic de RenderJob."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RenderJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    status: str  # queued | processing | completed | failed
    progress: float
    output_path: Optional[str]
    output_url: Optional[str] = None
    error: Optional[str]
    created_at: datetime
    updated_at: datetime


class RenderStartRequest(BaseModel):
    fps: int = 30