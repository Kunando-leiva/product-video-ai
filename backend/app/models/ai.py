"""Schemas HTTP de IA."""
from typing import Any, Optional

from pydantic import BaseModel, Field


class AIProviderInfo(BaseModel):
    name: str
    enabled: bool
    available: bool
    requires_internet: bool
    model: Optional[str] = None
    note: Optional[str] = None


class AIProvidersResponse(BaseModel):
    providers: list[AIProviderInfo]
    active: str


class AITextTestRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    system: Optional[str] = Field(default=None, max_length=2000)
    provider: Optional[str] = Field(default=None, max_length=40)
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    json_schema: Optional[dict[str, Any]] = None


class AITextTestResponse(BaseModel):
    text: str
    provider: str
    model: str
    tokens_in: int
    tokens_out: int


class AIScriptTestRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    product_description: str = Field(default="", max_length=4000)
    duration: int = Field(default=30, ge=10, le=600)
    style: str = Field(default="professional", max_length=40)
    provider: Optional[str] = Field(default=None, max_length=40)


class AIScriptSectionOut(BaseModel):
    text: str
    duration: float


class AIScriptTestResponse(BaseModel):
    hook: str
    sections: list[AIScriptSectionOut]
    cta: str
    provider: str
    model: str


class AIUsageRow(BaseModel):
    id: int
    provider: str
    task: str
    status: str
    tokens: int
    cost_estimate: float
    detail: Optional[str]
    created_at: str


class AIUsageResponse(BaseModel):
    rows: list[AIUsageRow]