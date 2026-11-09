"""TTS local con piper-tts.

Carga la voz de forma perezosa y la cachea.
"""
import logging
import shutil
import subprocess
import wave
from pathlib import Path

from app.audio.tts_provider import TextToSpeechProvider
from app.audio.voices import find_voice, list_voices
from app.core.errors import NotReadyError, ValidationError


log = logging.getLogger("app.audio.tts_local")


# Cache de modelos cargados: voice_id → modelo
_model_cache: dict = {}


class LocalPiperTTS(TextToSpeechProvider):
    name = "local_piper"

    def is_available(self) -> bool:
        # Vía 1: paquete piper-tts (import)
        try:
            from piper import PiperVoice  # noqa: F401
            if list_voices():
                return True
        except ImportError:
            pass
        # Vía 2: binario piper en el PATH
        if shutil.which("piper") and list_voices():
            return True
        return False

    def _load_piper_model(self, voice_id: str):
        """Carga el modelo piper en memoria (cacheado)."""
        if voice_id in _model_cache:
            return _model_cache[voice_id]

        try:
            from piper import PiperVoice
        except ImportError as e:
            raise NotReadyError(
                message="El motor de voz local no está instalado.",
                cause=str(e),
                solution=(
                    "Instalá piper-tts con: pip install piper-tts. "
                    "Ver la guía del Módulo 11."
                ),
            )

        v = find_voice(voice_id)
        log.info("Cargando voz '%s'…", voice_id)
        model = PiperVoice.load(str(v.onnx_path), config_path=str(v.config_path))
        _model_cache[voice_id] = model
        log.info("Voz '%s' lista.", voice_id)
        return model

    def synthesize(
        self,
        text: str,
        out_path: Path,
        voice_id: str | None = None,
        speed: float = 1.0,
    ) -> Path:
        if not text.strip():
            raise ValidationError(
                message="El texto para sintetizar está vacío.",
            )

        # Elegir voz por defecto: primera disponible
        voices = list_voices()
        if not voices:
            raise NotReadyError(
                message="No hay voces instaladas.",
                solution=(
                    "Descargá una voz con: "
                    "python scripts/download_voice.py es_AR-daniela-high"
                ),
            )
        voice_id = voice_id or voices[0].id

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Vía 1: paquete piper-tts (API Python)
        try:
            from piper import PiperVoice  # noqa: F401
            return self._synth_via_python(text, out_path, voice_id, speed)
        except ImportError:
            pass

        # Vía 2: binario piper
        if shutil.which("piper"):
            return self._synth_via_binary(text, out_path, voice_id, speed)

        raise NotReadyError(
            message="No se encontró piper (ni paquete ni binario).",
            solution="pip install piper-tts o instalá el binario y agregalo al PATH.",
        )

    # ------------------------------------------------------------------

    def _synth_via_python(
        self, text: str, out_path: Path, voice_id: str, speed: float
    ) -> Path:
        import wave

        model = self._load_piper_model(voice_id)
        # piper 1.2 API: synthesize(text, wav_file, length_scale=1/speed)
        length_scale = 1.0 / max(speed, 0.1)
        with wave.open(str(out_path), "wb") as wav_file:
            model.synthesize(text, wav_file, length_scale=length_scale)

        log.info("Voz generada (python): %s", out_path.name)
        return out_path

    def _synth_via_binary(
        self, text: str, out_path: Path, voice_id: str, speed: float
    ) -> Path:
        v = find_voice(voice_id)
        length_scale = 1.0 / max(speed, 0.1)

        cmd = [
            "piper",
            "--model", str(v.onnx_path),
            "--config", str(v.config_path),
            "--length_scale", f"{length_scale:.3f}",
            "--output_file", str(out_path),
        ]
        log.debug("piper cmd: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=120,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise ValidationError(
                message="La síntesis de voz tardó demasiado.",
                cause=str(e),
            ) from e

        if result.returncode != 0:
            raise ValidationError(
                message="piper falló al sintetizar la voz.",
                cause=(result.stderr or b"").decode("utf-8", "ignore")[-400:],
            )
        if not out_path.exists() or out_path.stat().st_size == 0:
            raise ValidationError(
                message="El WAV generado está vacío.",
            )

        log.info("Voz generada (binario): %s", out_path.name)
        return out_path

    # ------------------------------------------------------------------

    @staticmethod
    def probe_duration(wav_path: Path) -> float | None:
        """Duración en segundos de un WAV, sin ffprobe."""
        try:
            with wave.open(str(wav_path), "rb") as w:
                frames = w.getnframes()
                rate = w.getframerate()
                if rate:
                    return round(frames / rate, 3)
        except (wave.Error, OSError):
            return None
        return None