from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: str
    service: str = "voice-gateway"
    backend: str = "speaches"


class VoiceItem(BaseModel):
    id: str
    backend_voice: str
    active: bool = True


class VoicesResponse(BaseModel):
    default_voice: str
    unknown_voice_policy: str
    fallback_voice_id: str
    voices: list[VoiceItem]


class ModelItem(BaseModel):
    id: str
    object: str = "model"
    owned_by: str = "voice-gateway"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelItem]


class SpeechRequest(BaseModel):
    model: str = Field(..., examples=["tts-1"])
    input: str = Field(..., min_length=1)
    voice: str = "default"
    response_format: str = "mp3"
    speed: float = 1.0


class OpsModelRequest(BaseModel):
    model_id: str = Field(..., min_length=1)


class OpsPreviewRequest(BaseModel):
    model: str = Field(..., min_length=1)
    input: str = Field(..., min_length=1)
    voice: str = Field(..., min_length=1)
    response_format: str = "wav"
    speed: float = 1.0


class OpsPromotionPlanRequest(BaseModel):
    backend_tts_model: str = Field(..., min_length=1)
    fallback_voice_id: str = Field(default="default", min_length=1)
    unknown_voice_policy: str = "reject"
    include_default_alloy_aliases: bool = True
    voice_ids: list[str] = Field(default_factory=list)
