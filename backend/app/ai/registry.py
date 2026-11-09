"""Registry de proveedores de IA.

El AI Router (Módulo 15) consultará este registry para saber
qué proveedores existen y cuáles están disponibles.
"""
import logging

from app.ai.mock_provider import MockProvider
from app.ai.provider import AIProvider, AIProviderStatus


log = logging.getLogger("app.ai.registry")


# Orden de prioridad por defecto (Regla 20)
_DEFAULT_PRIORITY = ["local", "grok", "gemini", "deepseek", "mock"]


_registry: dict[str, AIProvider] = {}


def _ensure_loaded() -> None:
    global _registry
    if _registry:
        return
    # Solo el mock está registrado en el Módulo 13.
    # Módulos 14–16 agregarán "local", "grok", "gemini", "deepseek".
    _registry["mock"] = MockProvider()


def register(provider: AIProvider) -> None:
    _ensure_loaded()
    _registry[provider.name] = provider
    log.info("AI provider registrado: %s", provider.name)


def list_providers() -> list[AIProvider]:
    _ensure_loaded()
    return list(_registry.values())


def get_provider(name: str | None = None) -> AIProvider:
    """Devuelve el provider solicitado o el mejor disponible.

    Regla 20: el orden es configurable; aquí es local → ... → mock.
    """
    _ensure_loaded()

    if name and name in _registry:
        p = _registry[name]
        if p.is_available():
            return p
        log.warning("Provider '%s' no disponible; se elige el mejor.", name)

    for candidate in _DEFAULT_PRIORITY:
        p = _registry.get(candidate)
        if p and p.is_available():
            return p

    # Fallback final: mock (siempre disponible)
    return _registry["mock"]


def statuses() -> list[AIProviderStatus]:
    _ensure_loaded()
    return [p.status() for p in _registry.values()]