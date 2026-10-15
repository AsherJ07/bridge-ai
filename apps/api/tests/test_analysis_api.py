from __future__ import annotations

import os
import struct
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.analysis.media import cleanup_expired_uploads
from app.analysis.models import (
    AnalysisContent,
    AnalysisResult,
    AnalysisStage,
    EvidenceItem,
    InterpretationItem,
    TranscriptSegment,
    UsageMetadata,
)
from app.analysis.store import store
from app.main import app


def box(kind: bytes, payload: bytes) -> bytes:
    return (len(payload) + 8).to_bytes(4, "big") + kind + payload


def valid_mp4(duration_seconds: int = 12) -> bytes:
    ftyp = box(b"ftyp", b"isom" + b"\x00\x00\x02\x00" + b"isom")
    mvhd = box(
        b"mvhd",
        b"\x00\x00\x00\x00"
        + b"\x00" * 8
        + (1000).to_bytes(4, "big")
        + (duration_seconds * 1000).to_bytes(4, "big"),
    )
    return ftyp + box(b"moov", mvhd)


@pytest.fixture(autouse=True)
def isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store.clear()
    monkeypatch.setenv("BRIDGE_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("BRIDGE_UPLOAD_RETENTION_SECONDS", "3600")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    yield
    store.clear()


def upload(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/uploads",
        files={"file": ("clip.mp4", valid_mp4(), "video/mp4")},
    )
    assert response.status_code == 201
    return response.json()


def test_upload_validates_content_and_metadata(tmp_path: Path) -> None:
    with TestClient(app) as client:
        body = upload(client)
    assert body["duration_seconds"] == 12
    assert body["size_bytes"] == len(valid_mp4())
    assert len(body["sha256"]) == 64
    stored = list(tmp_path.iterdir())
    assert len(stored) == 1
    assert stored[0].name != "clip.mp4"


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "expected_status"),
    [
        ("clip.exe", "application/octet-stream", b"bad", 415),
        ("clip.mp4", "video/mp4", b"not a video", 415),
        ("clip.mp4", "video/mp4", valid_mp4(121), 413),
        ("clip.mp4", "video/mp4", box(b"ftyp", b"isom"), 422),
    ],
)
def test_upload_rejects_invalid_media(
    filename: str, content_type: str, content: bytes, expected_status: int
) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/uploads",
            files={"file": (filename, content, content_type)},
        )
    assert response.status_code == expected_status


def test_streaming_size_limit_removes_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.analysis.media.MAX_UPLOAD_BYTES", 10)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/uploads",
            files={"file": ("clip.mp4", valid_mp4(), "video/mp4")},
        )
    assert response.status_code == 413
    assert list(tmp_path.iterdir()) == []


def test_expired_file_cleanup_is_scoped_to_files(tmp_path: Path) -> None:
    stale = tmp_path / "stale.mp4"
    stale.write_bytes(b"old")
    nested = tmp_path / "directory"
    nested.mkdir()
    old = time.time() - 120
    stale.touch()
    os.utime(stale, (old, old))
    cleanup_expired_uploads(tmp_path, retention_seconds=60)
    assert not stale.exists()
    assert nested.exists()


def test_unconfigured_model_fails_honestly() -> None:
    with TestClient(app) as client:
        uploaded = upload(client)
        created = client.post(
            "/api/v1/analyses",
            json={"upload_id": uploaded["id"], "output_language": "Urdu"},
            headers={"Idempotency-Key": "test-request-1"},
        )
        assert created.status_code == 202
        analysis = client.get(f"/api/v1/analyses/{created.json()['id']}")
    assert analysis.status_code == 200
    assert analysis.json()["status"] == "failed"
    assert analysis.json()["error"]["code"] == "AI_NOT_CONFIGURED"
    assert analysis.json()["result"] is None


def test_analysis_success_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAnalyzer:
        def __init__(self, _settings: object) -> None:
            pass

        def analyze(self, *_args: object) -> AnalysisResult:
            on_stage = _args[-1]
            assert callable(on_stage)
            on_stage(AnalysisStage.ANALYZING)
            return AnalysisResult(
                content=AnalysisContent(
                    overview="A greeting.",
                    detected_languages=["English"],
                    transcript=[
                        TranscriptSegment(
                            id="segment_1", start_seconds=0, end_seconds=1, spoken_text="Hello"
                        )
                    ],
                    evidence=[
                        EvidenceItem(
                            id="evidence_1",
                            kind="transcript",
                            start_seconds=0,
                            end_seconds=1,
                            excerpt="Hello",
                            description="Spoken greeting",
                        )
                    ],
                    interpretations=[
                        InterpretationItem(
                            id="claim_1",
                            claim="The speaker greets the viewer.",
                            cultural_context="A conventional greeting.",
                            support_status="supported",
                            evidence_ids=["evidence_1"],
                        )
                    ],
                ),
                model_id="test-model",
                prompt_version="test-prompt",
                pipeline_version="test-pipeline",
                usage=UsageMetadata(input_tokens=10, output_tokens=5, total_tokens=15),
            )

    monkeypatch.setattr("app.analysis.routes.GeminiVideoAnalyzer", FakeAnalyzer)
    with TestClient(app) as client:
        uploaded = upload(client)
        created = client.post(
            "/api/v1/analyses",
            json={"upload_id": uploaded["id"]},
            headers={"Idempotency-Key": "successful-request"},
        )
        analysis = client.get(f"/api/v1/analyses/{created.json()['id']}")
    assert analysis.json()["status"] == "completed"
    assert analysis.json()["result"]["content"]["interpretations"][0]["evidence_ids"] == [
        "evidence_1"
    ]


def test_idempotency_and_cleanup() -> None:
    with TestClient(app) as client:
        uploaded = upload(client)
        payload = {"upload_id": uploaded["id"]}
        first = client.post(
            "/api/v1/analyses", json=payload, headers={"Idempotency-Key": "same-key"}
        )
        second = client.post(
            "/api/v1/analyses", json=payload, headers={"Idempotency-Key": "same-key"}
        )
        conflict = client.post(
            "/api/v1/analyses",
            json={**payload, "output_language": "Spanish"},
            headers={"Idempotency-Key": "same-key"},
        )
        deleted = client.delete(f"/api/v1/uploads/{uploaded['id']}")
        missing = client.delete(f"/api/v1/uploads/{uploaded['id']}")
    assert first.json()["id"] == second.json()["id"]
    assert conflict.status_code == 409
    assert deleted.status_code == 204
    assert missing.status_code == 404


def test_result_schema_rejects_unknown_evidence_and_bad_timing() -> None:
    with pytest.raises(ValueError, match="segment end"):
        TranscriptSegment(id="segment_1", start_seconds=2, end_seconds=1, spoken_text="x")
    with pytest.raises(ValueError, match="without evidence"):
        InterpretationItem(
            id="claim_1", claim="x", cultural_context="x", support_status="supported"
        )
    with pytest.raises(ValueError, match="require a caveat"):
        InterpretationItem(
            id="claim_1", claim="x", cultural_context="x", support_status="uncertain"
        )
    with pytest.raises(ValueError, match="unknown evidence"):
        AnalysisContent(
            overview="x",
            detected_languages=[],
            transcript=[],
            evidence=[],
            interpretations=[
                InterpretationItem(
                    id="claim_1",
                    claim="x",
                    cultural_context="x",
                    support_status="partial",
                    evidence_ids=["evidence_missing"],
                )
            ],
        )


def test_webm_duration_parser() -> None:
    # Minimal EBML marker + WebM doctype + TimecodeScale + float64 Duration (2 seconds).
    content = (
        b"\x1a\x45\xdf\xa3\x84webm"
        + b"\x2a\xd7\xb1\x83\x0f\x42\x40"
        + b"\x44\x89\x88"
        + struct.pack(">d", 2000.0)
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/uploads", files={"file": ("clip.webm", content, "video/webm")}
        )
    assert response.status_code == 201
    assert response.json()["duration_seconds"] == pytest.approx(2.0)
