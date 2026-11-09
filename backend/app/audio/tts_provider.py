"""Interfaz común de TTS (Regla 16).

La UI y los servicios no dependen de un proveedor específico.
El TTSRouter decide cuál usar según configuración.
"""
from abc import ABC, abstractmethod
from pathlib import Path


class TextToSpeechProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def is_available(self) -> bool:
        """Si el proveedor puede usarse ahora (binario/deps + voces)."""
        ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        out_path: Path,
        voice_id: str | None = None,
        speed: float = 1.0,
    ) -> Path:
        """Genera un WAV con la voz indicada.

        Args:
            text: texto a sintetizar (plano, sin SSML).
            out_path: ruta del WAV a generar.
            voice_id: identificador de voz (dependiente del proveedor).
            speed: multiplicador de velocidad (1.0 = normal).

        Returns:
            La ruta del WAV generado.
        """
        ...