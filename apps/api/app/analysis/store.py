from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock, Timer
from uuid import uuid4

from .models import (
    AnalysisError,
    AnalysisEvent,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisResult,
    AnalysisStage,
    AnalysisStatus,
    UploadResponse,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class StoredUpload:
    public: UploadResponse
    path: Path


class WorkflowStore:
    """Process-local workflow store; intentionally replaceable with durable persistence."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._uploads: dict[str, StoredUpload] = {}
        self._analyses: dict[str, AnalysisResponse] = {}
        self._idempotency: dict[str, tuple[str, str]] = {}

    def add_upload(self, upload: UploadResponse, path: Path, retention_seconds: int) -> None:
        with self._lock:
            self._uploads[upload.id] = StoredUpload(public=upload, path=path)
        cleanup = Timer(retention_seconds, self.delete_upload, args=(upload.id,))
        cleanup.daemon = True
        cleanup.start()

    def get_upload(self, upload_id: str) -> StoredUpload | None:
        with self._lock:
            return self._uploads.get(upload_id)

    def delete_upload(self, upload_id: str) -> bool:
        with self._lock:
            item = self._uploads.pop(upload_id, None)
        if item is None:
            return False
        item.path.unlink(missing_ok=True)
        return True

    def create_analysis(
        self, request: AnalysisRequest, idempotency_key: str | None
    ) -> tuple[AnalysisResponse, bool]:
        fingerprint = request.model_dump_json()
        with self._lock:
            if idempotency_key and idempotency_key in self._idempotency:
                existing_id, existing_fingerprint = self._idempotency[idempotency_key]
                if existing_fingerprint != fingerprint:
                    raise ValueError("idempotency key was already used for another request")
                return self._analyses[existing_id].model_copy(deep=True), False

            now = utc_now()
            analysis = AnalysisResponse(
                id=str(uuid4()),
                upload_id=request.upload_id,
                status=AnalysisStatus.QUEUED,
                stage=AnalysisStage.QUEUED,
                output_language=request.output_language,
                created_at=now,
                updated_at=now,
                events=[AnalysisEvent(stage=AnalysisStage.QUEUED, occurred_at=now)],
            )
            self._analyses[analysis.id] = analysis
            if idempotency_key:
                self._idempotency[idempotency_key] = (analysis.id, fingerprint)
            return analysis.model_copy(deep=True), True

    def get_analysis(self, analysis_id: str) -> AnalysisResponse | None:
        with self._lock:
            item = self._analyses.get(analysis_id)
            return item.model_copy(deep=True) if item else None

    def set_stage(self, analysis_id: str, stage: AnalysisStage) -> None:
        with self._lock:
            item = self._analyses[analysis_id]
            now = utc_now()
            item.stage = stage
            item.status = AnalysisStatus.PROCESSING
            item.updated_at = now
            item.events.append(AnalysisEvent(stage=stage, occurred_at=now))

    def complete(self, analysis_id: str, result: AnalysisResult) -> None:
        with self._lock:
            item = self._analyses[analysis_id]
            now = utc_now()
            item.stage = AnalysisStage.COMPLETED
            item.status = AnalysisStatus.COMPLETED
            item.updated_at = now
            item.result = result
            item.events.append(AnalysisEvent(stage=AnalysisStage.COMPLETED, occurred_at=now))

    def fail(self, analysis_id: str, error: AnalysisError) -> None:
        with self._lock:
            item = self._analyses[analysis_id]
            now = utc_now()
            item.stage = AnalysisStage.FAILED
            item.status = AnalysisStatus.FAILED
            item.updated_at = now
            item.error = error
            item.events.append(AnalysisEvent(stage=AnalysisStage.FAILED, occurred_at=now))

    def clear(self) -> None:
        with self._lock:
            uploads = list(self._uploads.values())
            self._uploads.clear()
            self._analyses.clear()
            self._idempotency.clear()
        for item in uploads:
            item.path.unlink(missing_ok=True)


store = WorkflowStore()
