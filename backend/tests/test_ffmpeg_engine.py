"""Tests del FFmpegEngine (Regla 66).

Si alguno de estos tests falla, DETENER el desarrollo y arreglar el motor.
"""
from pathlib import Path

import pytest

from app.core import ffmpeg
from app.video.engine import FFmpegEngine


pytestmark = pytest.mark.skipif(
    not ffmpeg.is_available(),
    reason="FFmpeg no disponible",
)


@pytest.fixture
def engine() -> FFmpegEngine:
    return FFmpegEngine()


@pytest.fixture
def video_2s(tmp_path: Path) -> Path:
    out = tmp_path / "v2s.mp4"
    ffmpeg.make_test_video(out, seconds=2.0, fps=24, size="320x240")
    return out


@pytest.fixture
def video_1s(tmp_path: Path) -> Path:
    out = tmp_path / "v1s.mp4"
    ffmpeg.make_test_video(out, seconds=1.0, fps=24, size="320x240")
    return out


@pytest.fixture
def image(tmp_path: Path) -> Path:
    out = tmp_path / "img.png"
    ffmpeg.make_solid_image(out, width=400, height=400, color="red")
    return out


@pytest.fixture
def audio(tmp_path: Path) -> Path:
    import subprocess
    out = tmp_path / "audio.m4a"
    subprocess.run(
        [
            ffmpeg.ffmpeg_path() or "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:a", "aac", "-b:a", "96k",
            str(out),
        ],
        capture_output=True,
        check=True,
    )
    return out


# ----------------------------------------------------------------------
# Operación: image → video
# ----------------------------------------------------------------------

def test_image_to_video(engine: FFmpegEngine, image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.mp4"
    engine.image_to_video(
        image_path=str(image),
        out_path=str(out),
        duration=2.0,
        width=320,
        height=320,
        fps=24,
    )
    assert out.exists()
    assert out.stat().st_size > 0
    d = ffmpeg.probe_duration(out)
    assert d is not None and 1.5 <= d <= 2.5, f"duración: {d}"


def test_image_to_video_contain(engine: FFmpegEngine, image: Path, tmp_path: Path) -> None:
    out = tmp_path / "out_contain.mp4"
    engine.image_to_video(
        image_path=str(image),
        out_path=str(out),
        duration=1.0,
        width=640,
        height=640,
        fps=24,
        fit="contain",
    )
    assert out.exists()


# ----------------------------------------------------------------------
# Operación: trim de video
# ----------------------------------------------------------------------

def test_trim_video(engine: FFmpegEngine, video_2s: Path, tmp_path: Path) -> None:
    out = tmp_path / "trim.mp4"
    engine.trim_video(
        in_path=str(video_2s),
        out_path=str(out),
        start=0.5,
        duration=1.0,
    )
    assert out.exists()
    d = ffmpeg.probe_duration(out)
    assert d is not None and 0.7 <= d <= 1.4, f"duración: {d}"


def test_trim_video_start_zero(engine: FFmpegEngine, video_2s: Path, tmp_path: Path) -> None:
    out = tmp_path / "trim0.mp4"
    engine.trim_video(str(video_2s), str(out), start=0.0, duration=0.8)
    assert out.exists()


# ----------------------------------------------------------------------
# Operación: concat
# ----------------------------------------------------------------------

def test_concat_videos(
    engine: FFmpegEngine,
    video_1s: Path,
    video_2s: Path,
    tmp_path: Path,
) -> None:
    out = tmp_path / "concat.mp4"
    engine.concat_videos([str(video_1s), str(video_2s)], str(out))
    assert out.exists()
    d = ffmpeg.probe_duration(out)
    assert d is not None
    # 1s + 2s = 3s aprox (puede variar levemente)
    assert 2.5 <= d <= 3.6, f"duración: {d}"


def test_concat_requires_two(engine: FFmpegEngine, video_1s: Path, tmp_path: Path) -> None:
    from app.core.errors import ValidationError

    with pytest.raises(ValidationError):
        engine.concat_videos([str(video_1s)], str(tmp_path / "x.mp4"))


# ----------------------------------------------------------------------
# Operación: merge audio
# ----------------------------------------------------------------------

def test_merge_audio_replace(
    engine: FFmpegEngine,
    video_2s: Path,
    audio: Path,
    tmp_path: Path,
) -> None:
    out = tmp_path / "with_audio.mp4"
    engine.merge_audio(
        video_path=str(video_2s),
        audio_path=str(audio),
        out_path=str(out),
        audio_volume=1.0,
        mix=False,
    )
    assert out.exists()

    # Verificar que tiene stream de audio
    info = ffmpeg.probe(out)
    types = [s.get("codec_type") for s in info.get("streams", [])]
    assert "audio" in types, f"streams: {types}"
    assert "video" in types


def test_merge_audio_mix(
    engine: FFmpegEngine,
    video_2s: Path,
    audio: Path,
    tmp_path: Path,
) -> None:
    # Primero: agregarle audio propio al video
    with_audio = tmp_path / "v_with_audio.mp4"
    engine.merge_audio(str(video_2s), str(audio), str(with_audio), mix=False)

    # Ahora mezclamos con otra pista
    out = tmp_path / "mixed.mp4"
    engine.merge_audio(
        video_path=str(with_audio),
        audio_path=str(audio),
        out_path=str(out),
        audio_volume=0.15,  # música baja
        video_volume=1.0,   # voz al 100%
        mix=True,
    )
    assert out.exists()
    info = ffmpeg.probe(out)
    types = [s.get("codec_type") for s in info.get("streams", [])]
    assert "audio" in types


# ----------------------------------------------------------------------
# Operación: overlay de texto
# ----------------------------------------------------------------------

def test_overlay_text(engine: FFmpegEngine, video_2s: Path, tmp_path: Path) -> None:
    out = tmp_path / "text.mp4"
    engine.overlay_text(
        in_path=str(video_2s),
        out_path=str(out),
        text="OFERTA ESPECIAL",
        position="bottom",
        font_size=32,
        color="yellow",
    )
    assert out.exists()
    assert out.stat().st_size > 0


def test_overlay_text_escapes_special(
    engine: FFmpegEngine, video_2s: Path, tmp_path: Path
) -> None:
    out = tmp_path / "text_esc.mp4"
    # Caracteres que romperían drawtext sin escapar
    engine.overlay_text(
        in_path=str(video_2s),
        out_path=str(out),
        text="50% OFF: 'ahora'",
        font_size=24,
    )
    assert out.exists()


# ----------------------------------------------------------------------
# Operación: resize_and_pad
# ----------------------------------------------------------------------

def test_resize_and_pad(
    engine: FFmpegEngine, video_2s: Path, tmp_path: Path
) -> None:
    out = tmp_path / "padded.mp4"
    engine.resize_and_pad(
        in_path=str(video_2s),
        out_path=str(out),
        width=360,
        height=640,
    )
    assert out.exists()
    info = ffmpeg.probe(out)
    vs = next(
        s for s in info["streams"] if s.get("codec_type") == "video"
    )
    assert int(vs["width"]) == 360
    assert int(vs["height"]) == 640


# ----------------------------------------------------------------------
# Ejecución de un plan
# ----------------------------------------------------------------------

def test_execute_plan(
    engine: FFmpegEngine,
    video_1s: Path,
    video_2s: Path,
    tmp_path: Path,
) -> None:
    """Plan: recortar dos videos y concatenarlos."""
    from app.video.plan import (
        ConcatVideosOp,
        TrimVideoOp,
        VideoPlan,
    )

    a = tmp_path / "a.mp4"
    b = tmp_path / "b.mp4"
    final = tmp_path / "final.mp4"

    plan = VideoPlan(
        operations=[
            TrimVideoOp(
                in_path=str(video_1s), out_path=str(a),
                start=0.0, duration=0.5,
            ),
            TrimVideoOp(
                in_path=str(video_2s), out_path=str(b),
                start=0.5, duration=0.5,
            ),
            ConcatVideosOp(in_paths=[str(a), str(b)], out_path=str(final)),
        ]
    )
    engine.execute_plan(plan)
    assert final.exists()
    d = ffmpeg.probe_duration(final)
    assert d is not None and 0.6 <= d <= 1.6, f"duración: {d}"