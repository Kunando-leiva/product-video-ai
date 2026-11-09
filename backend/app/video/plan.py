"""VideoPlan: contrato intermedio entre la IA y FFmpeg (Regla 43).

La IA NUNCA emite comandos FFmpeg. Emite un VideoPlan validado.
El Render Engine (Módulo 9) traduce el plan a llamadas al FFmpegEngine.
"""
from typing import Literal, Union

from pydantic import BaseModel, Field


class BaseOp(BaseModel):
    """Base model for operations.

    The discriminator is declared by each concrete operation so its
    ``Literal`` type is not an invalid narrowing of a mutable ``str`` field.
    """
    pass


class ImageToVideoOp(BaseOp):
    type: Literal["image_to_video"] = "image_to_video"
    image_path: str
    out_path: str
    duration: float = Field(gt=0, le=600)
    width: int = Field(gt=0, le=4096)
    height: int = Field(gt=0, le=4096)
    fps: int = Field(default=30, gt=0, le=120)
    fit: Literal["cover", "contain"] = "cover"


class TrimVideoOp(BaseOp):
    type: Literal["trim_video"] = "trim_video"
    in_path: str
    out_path: str
    start: float = Field(ge=0)
    duration: float = Field(gt=0, le=600)
    reencode: bool = True


class ConcatVideosOp(BaseOp):
    type: Literal["concat_videos"] = "concat_videos"
    in_paths: list[str] = Field(min_length=2)
    out_path: str


class MergeAudioOp(BaseOp):
    type: Literal["merge_audio"] = "merge_audio"
    video_path: str
    audio_path: str
    out_path: str
    audio_volume: float = Field(default=1.0, ge=0.0, le=4.0)
    video_volume: float = Field(default=0.0, ge=0.0, le=4.0)
    mix: bool = False


class OverlayTextOp(BaseOp):
    type: Literal["overlay_text"] = "overlay_text"
    in_path: str
    out_path: str
    text: str = Field(max_length=500)
    position: Literal["top", "center", "bottom"] = "bottom"
    font_size: int = Field(default=48, gt=0, le=300)
    color: str = "white"
    box: bool = True


class ResizeAndPadOp(BaseOp):
    type: Literal["resize_and_pad"] = "resize_and_pad"
    in_path: str
    out_path: str
    width: int = Field(gt=0, le=4096)
    height: int = Field(gt=0, le=4096)
    background: str = "black"


Operation = Union[
    ImageToVideoOp,
    TrimVideoOp,
    ConcatVideosOp,
    MergeAudioOp,
    OverlayTextOp,
    ResizeAndPadOp,
]


class VideoPlan(BaseModel):
    """Plan de edición. Lista ordenada de operaciones."""
    operations: list[Operation] = Field(default_factory=list)

    def validate_chain(self) -> None:
        """Verifica que cada operación tenga inputs existentes.

        Validación a nivel de negocio, no de sintaxis.
        """
        from pathlib import Path

        produced: set[str] = set()
        seen_outputs: set[str] = set()

        for i, op in enumerate(self.operations):
            for attr in ("in_path", "video_path", "audio_path"):
                p = getattr(op, attr, None)
                if p and p not in produced and not Path(p).exists():
                    raise ValueError(
                        f"Op #{i} ({op.type}): input inexistente {p!r}"
                    )
            for p in getattr(op, "in_paths", []) or []:
                if p not in produced and not Path(p).exists():
                    raise ValueError(
                        f"Op #{i} ({op.type}): input inexistente {p!r}"
                    )

            out = getattr(op, "out_path", None)
            if out:
                if out in seen_outputs:
                    raise ValueError(
                        f"Op #{i} ({op.type}): out_path duplicado {out!r}"
                    )
                seen_outputs.add(out)
                produced.add(out)