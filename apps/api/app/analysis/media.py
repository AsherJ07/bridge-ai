from __future__ import annotations

import hashlib
import os
import struct
import time
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from .models import UploadResponse
from .store import utc_now

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_DURATION_SECONDS = 120.0
CHUNK_SIZE = 1024 * 1024
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm"}
ALLOWED_DECLARED_TYPES = {"video/mp4", "video/quicktime", "video/webm"}


def cleanup_expired_uploads(upload_dir: Path, retention_seconds: int) -> None:
    if not upload_dir.exists():
        return
    cutoff = time.time() - retention_seconds
    for path in upload_dir.iterdir():
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)


def _read_box_header(data: bytes, offset: int) -> tuple[int, bytes, int] | None:
    if offset + 8 > len(data):
        return None
    size = int.from_bytes(data[offset : offset + 4], "big")
    kind = data[offset + 4 : offset + 8]
    header_size = 8
    if size == 1:
        if offset + 16 > len(data):
            return None
        size = int.from_bytes(data[offset + 8 : offset + 16], "big")
        header_size = 16
    elif size == 0:
        size = len(data) - offset
    if size < header_size or offset + size > len(data):
        return None
    return size, kind, header_size


def _find_mp4_duration(data: bytes, start: int = 0, end: int | None = None) -> float | None:
    boundary = len(data) if end is None else min(end, len(data))
    offset = start
    while offset + 8 <= boundary:
        header = _read_box_header(data, offset)
        if header is None:
            return None
        size, kind, header_size = header
        payload = offset + header_size
        if kind == b"mvhd":
            if payload + 20 > offset + size:
                return None
            version = data[payload]
            if version == 0:
                timescale = int.from_bytes(data[payload + 12 : payload + 16], "big")
                duration = int.from_bytes(data[payload + 16 : payload + 20], "big")
            elif version == 1 and payload + 32 <= offset + size:
                timescale = int.from_bytes(data[payload + 20 : payload + 24], "big")
                duration = int.from_bytes(data[payload + 24 : payload + 32], "big")
            else:
                return None
            return duration / timescale if timescale else None
        if kind in {b"moov", b"trak", b"mdia"}:
            found = _find_mp4_duration(data, payload, offset + size)
            if found is not None:
                return found
        offset += size
    return None


def _read_ebml_size(data: bytes, offset: int) -> tuple[int, int] | None:
    if offset >= len(data):
        return None
    first = data[offset]
    mask = 0x80
    length = 1
    while length <= 8 and not first & mask:
        mask >>= 1
        length += 1
    if length > 8 or offset + length > len(data):
        return None
    value = first & (mask - 1)
    for byte in data[offset + 1 : offset + length]:
        value = (value << 8) | byte
    return value, length


def _find_webm_duration(data: bytes) -> float | None:
    scale = 1_000_000
    scale_at = data.find(b"\x2a\xd7\xb1")
    if scale_at >= 0:
        parsed = _read_ebml_size(data, scale_at + 3)
        if parsed:
            size, width = parsed
            value_at = scale_at + 3 + width
            if 0 < size <= 8 and value_at + size <= len(data):
                scale = int.from_bytes(data[value_at : value_at + size], "big")
    duration_at = data.find(b"\x44\x89")
    if duration_at < 0:
        return None
    parsed = _read_ebml_size(data, duration_at + 2)
    if not parsed:
        return None
    size, width = parsed
    value_at = duration_at + 2 + width
    if size == 4 and value_at + size <= len(data):
        duration = struct.unpack(">f", data[value_at : value_at + size])[0]
    elif size == 8 and value_at + size <= len(data):
        duration = struct.unpack(">d", data[value_at : value_at + size])[0]
    else:
        return None
    return float(duration * scale / 1_000_000_000)


def inspect_media(path: Path) -> tuple[str, float]:
    data = path.read_bytes()
    if len(data) >= 12 and data[4:8] == b"ftyp":
        duration = _find_mp4_duration(data)
        brand = data[8:12]
        media_type = "video/quicktime" if brand == b"qt  " else "video/mp4"
    elif data.startswith(b"\x1a\x45\xdf\xa3") and b"webm" in data[:4096].lower():
        duration = _find_webm_duration(data[: 2 * 1024 * 1024])
        media_type = "video/webm"
    else:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File content is not MP4, MOV, or WebM"
        )
    if duration is None or duration <= 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Video duration could not be verified"
        )
    if duration > MAX_DURATION_SECONDS:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Video exceeds the 120-second limit")
    return media_type, duration


async def save_validated_upload(file: UploadFile, upload_dir: Path) -> tuple[UploadResponse, Path]:
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if not filename or suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Use an MP4, MOV, or WebM file")
    if file.content_type not in ALLOWED_DECLARED_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Declared media type is not supported"
        )

    upload_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    upload_id = str(uuid4())
    path = upload_dir / f"{upload_id}{suffix}"
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("xb") as destination:
            os.chmod(path, 0o600)
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status.HTTP_413_CONTENT_TOO_LARGE,
                        "Video exceeds the 100 MB limit",
                    )
                digest.update(chunk)
                destination.write(chunk)
        media_type, duration = inspect_media(path)
        if file.content_type == "video/webm" and media_type != "video/webm":
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File content does not match its media type"
            )
        response = UploadResponse(
            id=upload_id,
            filename=filename,
            media_type=media_type,
            size_bytes=size,
            duration_seconds=duration,
            sha256=digest.hexdigest(),
            created_at=utc_now(),
        )
        return response, path
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
