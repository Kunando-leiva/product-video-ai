"""Descarga una voz piper desde Hugging Face a models/tts/.

Uso:
    python scripts/download_voice.py es_AR-daniela-high
    python scripts/download_voice.py es_MX-ald-medium
    python scripts/download_voice.py            # lista las disponibles
"""
import argparse
import shutil
import sys
import urllib.request
from pathlib import Path


BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# Voces oficiales conocidas. Estructura: <id> -> (ruta, tamaño aprox MB)
KNOWN_VOICES = {
    # Español Argentina
    "es_AR-daniela-high":        ("es/es_AR/daniela/high/es_AR-daniela-high", 108),
    # Español México
    "es_MX-ald-medium":          ("es/es_MX/ald/medium/es_MX-ald-medium", 63),
    "es_MX-claude-high":         ("es/es_MX/claude/high/es_MX-claude-high", 108),
    # Español España
    "es_ES-davefx-medium":       ("es/es_ES/davefx/medium/es_ES-davefx-medium", 63),
    "es_ES-carlfm-x_low":        ("es/es_ES/carlfm/x_low/es_ES-carlfm-x_low", 20),
    "es_ES-mls_10246-low":       ("es/es_ES/mls_10246/low/es_ES-mls_10246-low", 20),
    "es_ES-mls_9972-low":        ("es/es_ES/mls_9972/low/es_ES-mls_9972-low", 20),
    # Inglés (por si hace falta)
    "en_US-lessac-medium":       ("en/en_US/lessac/medium/en_US-lessac-medium", 63),
    "en_US-amy-medium":          ("en/en_US/amy/medium/en_US-amy-medium", 63),
}


def _models_dir() -> Path:
    # backend/scripts/download_voice.py → repo_root/models/tts
    here = Path(__file__).resolve()
    repo_root = here.parents[2]
    d = repo_root / "models" / "tts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  ✓ Ya existe {dest.name}")
        return
    print(f"  ↓ {url}")
    with urllib.request.urlopen(url) as r, dest.open("wb") as f:
        shutil.copyfileobj(r, f)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  ✓ {dest.name} ({size_mb:.1f} MB)")


def download_voice(voice_id: str) -> None:
    if voice_id not in KNOWN_VOICES:
        print(f"✗ Voz desconocida: {voice_id}")
        print("\nVoces disponibles:")
        for k in sorted(KNOWN_VOICES):
            print(f"  {k}")
        sys.exit(1)

    rel, _ = KNOWN_VOICES[voice_id]
    dest_dir = _models_dir()

    onnx_url = f"{BASE}/{rel}.onnx"
    json_url = f"{BASE}/{rel}.onnx.json"

    print(f"Descargando voz '{voice_id}' a {dest_dir}…")
    _download(onnx_url, dest_dir / f"{voice_id}.onnx")
    _download(json_url, dest_dir / f"{voice_id}.onnx.json")
    print("\n✓ Listo. Reiniciá el backend para que detecte la voz.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga voces piper")
    parser.add_argument(
        "voice_id",
        nargs="?",
        help="ID de la voz (ej: es_AR-daniela-high)",
    )
    args = parser.parse_args()

    if not args.voice_id:
        print("Voces disponibles:\n")
        for k, (_, mb) in sorted(KNOWN_VOICES.items()):
            print(f"  {k:<30} ~{mb} MB")
        print("\nEjemplo: python scripts/download_voice.py es_AR-daniela-high")
        return

    download_voice(args.voice_id)


if __name__ == "__main__":
    main()