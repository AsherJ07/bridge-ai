from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Header,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError

from .gemini import AnalysisConfigurationError, GeminiVideoAnalyzer, ModelProcessingError
from .media import cleanup_expired_uploads, save_validated_upload
from .models import (
    AnalysisError,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStage,
    UploadResponse,
)
from .settings import load_analysis_settings
from .store import store

router = APIRouter(prefix="/api/v1", tags=["analysis"])


def run_analysis(analysis_id: str, request: AnalysisRequest) -> None:
    upload = store.get_upload(request.upload_id)
    if upload is None:
        store.fail(
            analysis_id,
            AnalysisError(
                code="UPLOAD_NOT_FOUND", message="The uploaded video is no longer available."
            ),
        )
        return
    analyzer = GeminiVideoAnalyzer(load_analysis_settings())
    try:
        store.set_stage(analysis_id, AnalysisStage.VALIDATING)
        result = analyzer.analyze(
            upload.path,
            upload.public.media_type,
            request,
            lambda stage: store.set_stage(analysis_id, stage),
        )
        store.complete(analysis_id, result)
    except AnalysisConfigurationError as exc:
        store.fail(
            analysis_id,
            AnalysisError(code="AI_NOT_CONFIGURED", message=str(exc), retryable=False),
        )
    except (ModelProcessingError, ValidationError) as exc:
        store.fail(
            analysis_id,
            AnalysisError(code="INVALID_MODEL_RESULT", message=str(exc), retryable=True),
        )
    except Exception:
        store.fail(
            analysis_id,
            AnalysisError(
                code="ANALYSIS_PROVIDER_ERROR",
                message="The analysis provider request failed. Try again later.",
                retryable=True,
            ),
        )


@router.post("/uploads", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(file: Annotated[UploadFile, File(...)]) -> UploadResponse:
    settings = load_analysis_settings()
    cleanup_expired_uploads(settings.upload_dir, settings.upload_retention_seconds)
    upload, path = await save_validated_upload(file, settings.upload_dir)
    store.add_upload(upload, path, settings.upload_retention_seconds)
    return upload


@router.delete("/uploads/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(upload_id: str) -> Response:
    if not store.delete_upload(upload_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Upload not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/analyses", response_model=AnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
def create_analysis(
    payload: AnalysisRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: Annotated[str | None, Header(max_length=128)] = None,
) -> AnalysisResponse:
    if store.get_upload(payload.upload_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Upload not found")
    try:
        analysis, created = store.create_analysis(payload, idempotency_key)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if created:
        background_tasks.add_task(run_analysis, analysis.id, payload)
    return analysis


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: str) -> AnalysisResponse:
    analysis = store.get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return analysis
