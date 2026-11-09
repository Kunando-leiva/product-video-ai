"""Interfaz común de proveedores de IA (Regla 19).

Regla 57: la IA NUNCA devuelve comandos FFmpeg.
Solo texto, JSON validado o análisis. La traducción a comandos
la hace el Render Engine (Módulo 9).

Todos los métodos son async para que los providers cloud (HTTP)
y locales (subprocess/modelo) tengan la misma firma.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal, Optional


# ---------------------------------------------------------------------------
# DTOs de entrada/salida
# ---------------------------------------------------------------------------

@dataclass
class AITextRequest:
    """Solicitud de generación de texto."""
    prompt: str
    system: Optional[str] = None
    max_tokens: int = 512
    temperature: float = 0.7
    json_schema: Optional[dict[str, Any]] = None  # si se pide salida JSON


@dataclass
class AITextResponse:
    text: str
    model: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0
    raw: Optional[dict[str, Any]] = None


@dataclass
class AIScriptRequest:
    """Solicitud de guion promocional (Regla 18)."""
    product_name: str
    product_description: str = ""
    duration: int = 30
    style: str = "professional"
    language: str = "es"


@dataclass
class AIScriptSection:
    text: str
    duration: float


@dataclass
class AIScriptResponse:
    hook: str
    sections: list[AIScriptSection]
    cta: str
    provider: str
    model: str


@dataclass
class AIImageAnalysis:
    """Resultado del análisis de una imagen."""
    description: str
    tags: list[str] = field(default_factory=list)
    is_product: bool = False
    quality_score: float = 0.5
    provider: str = ""
    model: str = ""


@dataclass
class AIVideoAnalysis:
    """Resultado del análisis de un video."""
    description: str
    scenes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    quality_score: float = 0.5
    provider: str = ""
    model: str = ""


@dataclass
class AIProviderStatus:
    """Estado de un proveedor (Regla 21)."""
    name: str
    enabled: bool
    available: bool
    requires_internet: bool
    model: Optional[str] = None
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# Interfaz abstracta
# ---------------------------------------------------------------------------

class AIProvider(ABC):
    """Interfaz común. Cada proveedor concreto la implementa."""

    name: str = "abstract"
    requires_internet: bool = False
    default_model: Optional[str] = None

    # --- Capacidades -------------------------------------------------------

    @abstractmethod
    def is_available(self) -> bool:
        """Si el proveedor puede usarse AHORA (deps + configuración)."""
        ...

    @abstractmethod
    async def generate_text(self, req: AITextRequest) -> AITextResponse:
        """Genera texto libre o JSON a partir de un prompt."""
        ...

    @abstractmethod
    async def analyze_image(
        self, image_path: str, prompt: Optional[str] = None
    ) -> AIImageAnalysis:
        """Analiza una imagen del producto."""
        ...

    @abstractmethod
    async def analyze_video(
        self, video_path: str, prompt: Optional[str] = None
    ) -> AIVideoAnalysis:
        """Analiza un video del producto."""
        ...

    @abstractmethod
    async def generate_script(self, req: AIScriptRequest) -> AIScriptResponse:
        """Genera un guion promocional estructurado."""
        ...

    # --- Estado ------------------------------------------------------------

    def status(self) -> AIProviderStatus:
        return AIProviderStatus(
            name=self.name,
            enabled=True,
            available=self.is_available(),
            requires_internet=self.requires_internet,
            model=self.default_model,
        )