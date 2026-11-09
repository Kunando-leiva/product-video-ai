"""Modelos ORM (tablas SQLAlchemy).

Regla 45: projects, media, timeline_items, ai_providers, ai_usage,
render_jobs, templates, settings.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), default="")
    product_description: Mapped[str] = mapped_column(Text, default="")
    product_url: Mapped[str] = mapped_column(String(2000), default="")
    duration: Mapped[int] = mapped_column(Integer, default=60)
    format: Mapped[str] = mapped_column(String(8), default="9:16")
    style: Mapped[str] = mapped_column(String(40), default="professional")

    voice_enabled: Mapped[bool] = mapped_column(default=True)
    voice_provider: Mapped[str] = mapped_column(String(40), default="local")
    voice_name: Mapped[str] = mapped_column(String(80), default="default")

    subtitles_enabled: Mapped[bool] = mapped_column(default=True)
    subtitles_style: Mapped[str] = mapped_column(String(40), default="modern")

    music_enabled: Mapped[bool] = mapped_column(default=True)
    music_track: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    music_volume: Mapped[float] = mapped_column(Float, default=0.15)

    script_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timeline_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

   

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    media: Mapped[list["Media"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    timeline_items: Mapped[list["TimelineItem"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    render_jobs: Mapped[list["RenderJob"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

      # NUEVO (Módulo 12)
    voice_track: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    voice_volume: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0, server_default="1.0"
    )
    


class Media(Base):
    __tablename__ = "media"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(16))  # image | video | audio
    filename: Mapped[str] = mapped_column(String(500))
    original_name: Mapped[str] = mapped_column(String(500))
    path: Mapped[str] = mapped_column(String(2000))

    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    orientation: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    thumbnail_path: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    project: Mapped[Project] = relationship(back_populates="media")


class TimelineItem(Base):
    __tablename__ = "timeline_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    media_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("media.id", ondelete="SET NULL"), nullable=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    start: Mapped[float] = mapped_column(Float, default=0.0)
    duration: Mapped[float] = mapped_column(Float, default=3.0)
    effect: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    project: Mapped[Project] = relationship(back_populates="timeline_items")


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # local, grok...
    enabled: Mapped[bool] = mapped_column(default=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    quota_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )


class AIUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    task: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20))  # success | error | quota
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RenderJob(Base):
    __tablename__ = "render_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    output_path: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    project: Mapped[Project] = relationship(back_populates="render_jobs")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AppSetting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )