from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisStage(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    UPLOADING_TO_MODEL = "uploading_to_model"
    WAITING_FOR_MODEL_FILE = "waiting_for_model_file"
    ANALYZING = "analyzing"
    VALIDATING_RESULT = "validating_result"
    COMPLETED = "completed"
    FAILED = "failed"


class OutputLanguage(StrEnum):
    ENGLISH = "English"
    URDU = "Urdu"
    HINDI = "Hindi"
    SPANISH = "Spanish"


class UploadResponse(BaseModel):
    id: str
    filename: str
    media_type: Literal["video/mp4", "video/quicktime", "video/webm"]
    size_bytes: int
    duration_seconds: float
    sha256: str
    created_at: datetime


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    upload_id: str = Field(min_length=1, max_length=64)
    output_language: OutputLanguage = OutputLanguage.ENGLISH
    source_language_hint: str | None = Field(default=None, max_length=80)
    caption: str | None = Field(default=None, max_length=500)
    context: str | None = Field(default=None, max_length=1000)


class TranscriptSegment(BaseModel):
    id: str = Field(pattern=r"^segment_[A-Za-z0-9_-]+$")
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    spoken_text: str
    translated_text: str | None = None

    @model_validator(mode="after")
    def validate_timing(self) -> TranscriptSegment:
        if self.end_seconds < self.start_seconds:
            raise ValueError("segment end must not precede its start")
        return self


class EvidenceItem(BaseModel):
    id: str = Field(pattern=r"^evidence_[A-Za-z0-9_-]+$")
    kind: Literal["transcript", "visual", "audio", "user_context"]
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    excerpt: str | None = None
    description: str


class InterpretationItem(BaseModel):
    id: str = Field(pattern=r"^claim_[A-Za-z0-9_-]+$")
    claim: str
    literal_translation: str | None = None
    cultural_context: str
    support_status: Literal["supported", "partial", "uncertain"]
    evidence_ids: list[str] = Field(default_factory=list)
    caveat: str | None = None

    @model_validator(mode="after")
    def require_evidence_or_abstention(self) -> InterpretationItem:
        if not self.evidence_ids and self.support_status != "uncertain":
            raise ValueError("claims without evidence must be marked uncertain")
        if self.support_status == "uncertain" and not self.caveat:
            raise ValueError("uncertain claims require a caveat")
        return self


class AnalysisContent(BaseModel):
    overview: str
    detected_languages: list[str]
    transcript: list[TranscriptSegment]
    evidence: list[EvidenceItem]
    interpretations: list[InterpretationItem]
    tone_and_humor: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence_references(self) -> AnalysisContent:
        evidence_ids = {item.id for item in self.evidence}
        for item in self.interpretations:
            missing = set(item.evidence_ids) - evidence_ids
            if missing:
                raise ValueError(f"unknown evidence references: {sorted(missing)}")
        return self


class UsageMetadata(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class AnalysisResult(BaseModel):
    content: AnalysisContent
    model_id: str
    model_version: str | None = None
    prompt_version: str
    pipeline_version: str
    usage: UsageMetadata


class AnalysisEvent(BaseModel):
    stage: AnalysisStage
    occurred_at: datetime


class AnalysisError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class AnalysisResponse(BaseModel):
    id: str
    upload_id: str
    status: AnalysisStatus
    stage: AnalysisStage
    output_language: OutputLanguage
    created_at: datetime
    updated_at: datetime
    events: list[AnalysisEvent]
    result: AnalysisResult | None = None
    error: AnalysisError | None = None
