"""Lógica de negocio de IA (solo descubrimiento y tests en este módulo)."""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import usage as usage_mod
from app.ai.provider import AIScriptRequest, AITextRequest
from app.ai.registry import get_provider, list_providers, statuses
from app.core.errors import NotFoundError, ValidationError
from app.models.ai import (
    AIProviderInfo,
    AIProvidersResponse,
    AIScriptTestRequest,
    AIScriptTestResponse,
    AIScriptSectionOut,
    AITextTestRequest,
    AITextTestResponse,
    AIUsageResponse,
    AIUsageRow,
)
from app.models.db_models import AIUsage


log = logging.getLogger("app.services.ai")


class AIService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    async def list_providers(self) -> AIProvidersResponse:
        stats = statuses()
        active = get_provider().name
        return AIProvidersResponse(
            providers=[
                AIProviderInfo(
                    name=s.name,
                    enabled=s.enabled,
                    available=s.available,
                    requires_internet=s.requires_internet,
                    model=s.model,
                    note=s.note,
                )
                for s in stats
            ],
            active=active,
        )

    async def provider_detail(self, name: str) -> AIProviderInfo:
        for p in list_providers():
            if p.name == name:
                s = p.status()
                return AIProviderInfo(
                    name=s.name,
                    enabled=s.enabled,
                    available=s.available,
                    requires_internet=s.requires_internet,
                    model=s.model,
                    note=s.note,
                )
        raise NotFoundError(
            message=f"No existe el proveedor de IA “{name}”.",
        )

    # ------------------------------------------------------------------
    # Texto
    # ------------------------------------------------------------------

    async def test_text(self, req: AITextTestRequest) -> AITextTestResponse:
        if not req.prompt.strip():
            raise ValidationError(message="El prompt está vacío.")

        provider = get_provider(req.provider)

        try:
            resp = await provider.generate_text(
                AITextRequest(
                    prompt=req.prompt,
                    system=req.system,
                    max_tokens=req.max_tokens,
                    temperature=req.temperature,
                    json_schema=req.json_schema,
                )
            )
        except Exception as e:
            await usage_mod.record(
                self.session, provider.name, "generate_text", "error",
                detail=f"{type(e).__name__}: {e}",
            )
            raise

        await usage_mod.record(
            self.session, provider.name, "generate_text", "success",
            tokens=resp.tokens_in + resp.tokens_out,
        )
        return AITextTestResponse(
            text=resp.text,
            provider=resp.provider,
            model=resp.model,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
        )

    # ------------------------------------------------------------------
    # Guion
    # ------------------------------------------------------------------

    async def test_script(
        self, req: AIScriptTestRequest
    ) -> AIScriptTestResponse:
        provider = get_provider(req.provider)

        try:
            resp = await provider.generate_script(
                AIScriptRequest(
                    product_name=req.product_name,
                    product_description=req.product_description,
                    duration=req.duration,
                    style=req.style,
                )
            )
        except Exception as e:
            await usage_mod.record(
                self.session, provider.name, "generate_script", "error",
                detail=f"{type(e).__name__}: {e}",
            )
            raise

        await usage_mod.record(
            self.session, provider.name, "generate_script", "success",
        )
        return AIScriptTestResponse(
            hook=resp.hook,
            sections=[
                AIScriptSectionOut(text=s.text, duration=s.duration)
                for s in resp.sections
            ],
            cta=resp.cta,
            provider=resp.provider,
            model=resp.model,
        )

    # ------------------------------------------------------------------
    # Uso
    # ------------------------------------------------------------------

    async def usage(self, limit: int = 50) -> AIUsageResponse:
        result = await self.session.execute(
            select(AIUsage)
            .order_by(AIUsage.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return AIUsageResponse(
            rows=[
                AIUsageRow(
                    id=r.id,
                    provider=r.provider,
                    task=r.task,
                    status=r.status,
                    tokens=r.tokens,
                    cost_estimate=r.cost_estimate,
                    detail=r.detail,
                    created_at=r.created_at.isoformat(),
                )
                for r in rows
            ]
        )