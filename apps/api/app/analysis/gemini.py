from __future__ import annotations

import json
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from google import genai
from google.genai import types

from .models import AnalysisContent, AnalysisRequest, AnalysisResult, AnalysisStage, UsageMetadata
from .settings import AnalysisSettings

PROMPT_VERSION = "video-analysis.v1"
PIPELINE_VERSION = "analysis-pipeline.v1"


class AnalysisConfigurationError(RuntimeError):
    """Raised when live analysis is not configured."""


class ModelProcessingError(RuntimeError):
    """Raised when the provider cannot produce a valid result."""


class GeminiVideoAnalyzer:
    def __init__(self, settings: AnalysisSettings) -> None:
        self.settings = settings

    def analyze(
        self,
        path: Path,
        media_type: str,
        request: AnalysisRequest,
        on_stage: Callable[[AnalysisStage], None],
    ) -> AnalysisResult:
        if not self.settings.gemini_api_key:
            raise AnalysisConfigurationError(
                "Live analysis is unavailable because GEMINI_API_KEY is not configured."
            )

        client = genai.Client(api_key=self.settings.gemini_api_key)
        remote_file: types.File | None = None
        try:
            on_stage(AnalysisStage.UPLOADING_TO_MODEL)
            remote_file = client.files.upload(
                file=path,
                config=types.UploadFileConfig(mime_type=media_type, display_name=path.name),
            )
            deadline = time.monotonic() + self.settings.gemini_timeout_seconds
            while remote_file.state == types.FileState.PROCESSING:
                on_stage(AnalysisStage.WAITING_FOR_MODEL_FILE)
                if time.monotonic() >= deadline:
                    raise ModelProcessingError(
                        "The model provider timed out while preparing the video."
                    )
                time.sleep(2)
                if not remote_file.name:
                    raise ModelProcessingError(
                        "The model provider returned a file without an identifier."
                    )
                remote_file = client.files.get(name=remote_file.name)
            if remote_file.state != types.FileState.ACTIVE:
                raise ModelProcessingError(
                    "The model provider could not prepare the uploaded video."
                )

            on_stage(AnalysisStage.ANALYZING)
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=[remote_file, self._prompt(request)],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AnalysisContent,
                    temperature=0.1,
                ),
            )
            on_stage(AnalysisStage.VALIDATING_RESULT)
            if isinstance(response.parsed, AnalysisContent):
                content = response.parsed
            elif response.text:
                content = AnalysisContent.model_validate_json(response.text)
            else:
                raise ModelProcessingError("The model provider returned no structured analysis.")

            usage = response.usage_metadata
            return AnalysisResult(
                content=content,
                model_id=self.settings.gemini_model,
                model_version=response.model_version,
                prompt_version=PROMPT_VERSION,
                pipeline_version=PIPELINE_VERSION,
                usage=UsageMetadata(
                    input_tokens=(usage.prompt_token_count or 0) if usage else 0,
                    output_tokens=(usage.candidates_token_count or 0) if usage else 0,
                    total_tokens=(usage.total_token_count or 0) if usage else 0,
                ),
            )
        finally:
            if remote_file and remote_file.name:
                # Production should enqueue a durable retry if provider cleanup fails.
                with suppress(Exception):
                    client.files.delete(name=remote_file.name)

    @staticmethod
    def _prompt(request: AnalysisRequest) -> str:
        context = json.dumps(
            {
                "output_language": request.output_language,
                "source_language_hint": request.source_language_hint,
                "user_caption": request.caption,
                "user_context": request.context,
            },
            ensure_ascii=False,
        )
        return f"""You are Bridge, an evidence-first cultural video analyst.

Return only the requested structured schema. Analyze only what the video and the explicitly
delimited user context support. Separate literal translation from cultural interpretation.
Every non-uncertain interpretation must cite IDs from your evidence array. Never invent a
positive entailment or source. When the relationship is unsupported or ambiguous, mark it
uncertain and explain the limitation in caveat. Do not treat a heuristic as a probability.
Use stable IDs: segment_1, evidence_1, claim_1, and so on. Preserve timestamps.

USER_CONTEXT_JSON_START
{context}
USER_CONTEXT_JSON_END
"""
