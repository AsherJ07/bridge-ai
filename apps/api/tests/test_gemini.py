from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from google.genai import types

from app.analysis.gemini import AnalysisConfigurationError, GeminiVideoAnalyzer
from app.analysis.models import (
    AnalysisContent,
    AnalysisRequest,
    AnalysisStage,
    InterpretationItem,
)
from app.analysis.settings import AnalysisSettings


def test_analyzer_refuses_to_run_without_api_key(tmp_path: Path) -> None:
    analyzer = GeminiVideoAnalyzer(AnalysisSettings(GEMINI_API_KEY=None))
    with pytest.raises(AnalysisConfigurationError, match="GEMINI_API_KEY"):
        analyzer.analyze(
            tmp_path / "missing.mp4",
            "video/mp4",
            AnalysisRequest(upload_id="upload-1"),
            lambda _stage: None,
        )


def test_analyzer_uses_structured_result_and_deletes_remote_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    processing = SimpleNamespace(state=types.FileState.PROCESSING, name="files/clip")
    active = SimpleNamespace(state=types.FileState.ACTIVE, name="files/clip")
    content = AnalysisContent(
        overview="Ambiguous greeting",
        detected_languages=["English"],
        transcript=[],
        evidence=[],
        interpretations=[
            InterpretationItem(
                id="claim_1",
                claim="The intent is unclear.",
                cultural_context="There is not enough context.",
                support_status="uncertain",
                caveat="No surrounding conversation is available.",
            )
        ],
    )
    calls: dict[str, object] = {}

    class FakeFiles:
        def upload(self, **kwargs: object) -> object:
            calls["upload"] = kwargs
            return processing

        def get(self, **kwargs: object) -> object:
            calls["get"] = kwargs
            return active

        def delete(self, **kwargs: object) -> None:
            calls["delete"] = kwargs

    class FakeModels:
        def generate_content(self, **kwargs: object) -> object:
            calls["generate"] = kwargs
            return SimpleNamespace(
                parsed=content,
                text=None,
                model_version="test-version",
                usage_metadata=SimpleNamespace(
                    prompt_token_count=100,
                    candidates_token_count=25,
                    total_token_count=125,
                ),
            )

    class FakeClient:
        def __init__(self, api_key: str) -> None:
            calls["api_key"] = api_key
            self.files = FakeFiles()
            self.models = FakeModels()

    monkeypatch.setattr("app.analysis.gemini.genai.Client", FakeClient)
    monkeypatch.setattr("app.analysis.gemini.time.sleep", lambda _seconds: None)
    stages: list[AnalysisStage] = []
    analyzer = GeminiVideoAnalyzer(AnalysisSettings(GEMINI_API_KEY="secret", GEMINI_MODEL="test"))
    result = analyzer.analyze(
        video,
        "video/mp4",
        AnalysisRequest(upload_id="upload-1", context="A friend sent this."),
        stages.append,
    )

    assert result.content == content
    assert result.usage.total_tokens == 125
    assert result.model_version == "test-version"
    assert stages == [
        AnalysisStage.UPLOADING_TO_MODEL,
        AnalysisStage.WAITING_FOR_MODEL_FILE,
        AnalysisStage.ANALYZING,
        AnalysisStage.VALIDATING_RESULT,
    ]
    assert calls["get"] == {"name": "files/clip"}
    assert calls["delete"] == {"name": "files/clip"}
    generated = calls["generate"]
    assert isinstance(generated, dict)
    assert "USER_CONTEXT_JSON_START" in generated["contents"][1]  # type: ignore[index]
