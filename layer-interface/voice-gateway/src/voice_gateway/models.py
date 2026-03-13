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


class SpeakerItem(BaseModel):
    id: str
    mode: str = "builtin"
    backend_speaker: str | None = None
    active: bool = True
    available: bool = True


class SpeakersResponse(BaseModel):
    default_voice: str
    discovered_builtin_speakers: list[str]
    voices: list[SpeakerItem]


class SpeechRequest(BaseModel):
    model: str = Field(..., examples=["xtts-v2"])
    input: str = Field(..., min_length=1)
    voice: str = "default"
    response_format: str = "wav"
    language: str = "en"
