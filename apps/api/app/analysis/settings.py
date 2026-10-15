from __future__ import annotations

import tempfile
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnalysisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.8-flash", validation_alias="GEMINI_MODEL")
    upload_dir: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "bridge-uploads",
        validation_alias="BRIDGE_UPLOAD_DIR",
    )
    cors_origin: str = Field(default="http://localhost:3000", validation_alias="BRIDGE_CORS_ORIGIN")
    gemini_timeout_seconds: int = Field(
        default=180, ge=30, le=600, validation_alias="GEMINI_TIMEOUT_SECONDS"
    )
    upload_retention_seconds: int = Field(
        default=3600, ge=60, le=86400, validation_alias="BRIDGE_UPLOAD_RETENTION_SECONDS"
    )


def load_analysis_settings() -> AnalysisSettings:
    return AnalysisSettings()
