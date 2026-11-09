"""Catálogo de voces piper disponibles en models/tts/."""
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.config import settings


log = logging.getLogger("app.audio.voices")


@dataclass
class VoiceInfo:
    id: str
    name: str
    language: str
    quality: str
    gender: Optional[str]
    onnx_path: Path
    config_path: Path


def voices_dir() -> Path:
    d = settings.MODELS_DIR / "tts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _parse_name(stem: str) -> tuple[str, str, str, Optional[str]]:
    """'es_AR-daniela-high' → ('es_AR', 'daniela', 'high', 'female').

    No hay metadata de género confiable en el nombre; inferimos por
    heurística conocida de las voces oficiales.
    """
    parts = stem.split("-")
    language = parts[0] if parts else "xx_XX"
    name = parts[1] if len(parts) > 1 else stem
    quality = parts[2] if len(parts) > 2 else "medium"

    # Heurística de género (nombres conocidos)
    female_names = {
        "daniela", "ald", "claude", "siwis", "mls_10246", "mls_9972",
        "karen", "cori", "carlotta", "elsa", "lisa", "paola",
    }
    male_names = {"davefx", "jorge", "diego", "carlos", "aldo", "marco"}

    gender = None
    if name.lower() in female_names:
        gender = "female"
    elif name.lower() in male_names:
        gender = "male"
    return language, name, quality, gender


def list_voices() -> list[VoiceInfo]:
    """Devuelve las voces instaladas (pares .onnx + .onnx.json)."""
    root = voices_dir()
    voices: list[VoiceInfo] = []
    for onnx in sorted(root.glob("*.onnx")):
        cfg = onnx.with_suffix(".onnx.json")
        if not cfg.exists():
            log.warning("Voz sin config: %s", onnx.name)
            continue

        stem = onnx.stem  # 'es_AR-daniela-high'
        lang, name, quality, gender = _parse_name(stem)

        # Intentar leer el JSON para sacar metadata real (language, etc.)
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            lang = data.get("language", {}).get("code", lang) or lang
            # piper a veces trae 'dataset' o 'speaker_id_map' con género
        except (OSError, json.JSONDecodeError):
            pass

        voices.append(
            VoiceInfo(
                id=stem,
                name=name,
                language=lang,
                quality=quality,
                gender=gender,
                onnx_path=onnx,
                config_path=cfg,
            )
        )
    return voices


def find_voice(voice_id: str) -> VoiceInfo:
    """Lanza si no encuentra la voz."""
    from app.core.errors import NotFoundError

    for v in list_voices():
        if v.id == voice_id:
            return v
    raise NotFoundError(
        message=f"No existe la voz “{voice_id}”.",
        solution=(
            "Descargá una voz con: python scripts/download_voice.py es_AR-daniela-high"
        ),
    )