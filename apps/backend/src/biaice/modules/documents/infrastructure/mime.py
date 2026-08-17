"""FR-02 MIME type detection service."""

from __future__ import annotations

from biaice.modules.documents.domain.models import DocumentMimeCategory

ALLOWED_MIME_TYPES: dict[str, DocumentMimeCategory] = {
    "application/pdf": DocumentMimeCategory.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentMimeCategory.DOCX,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentMimeCategory.XLSX,
    "image/png": DocumentMimeCategory.IMAGE,
    "image/jpeg": DocumentMimeCategory.IMAGE,
    "image/tiff": DocumentMimeCategory.IMAGE,
    "image/webp": DocumentMimeCategory.IMAGE,
    "application/zip": DocumentMimeCategory.ARCHIVE,
    "application/x-zip-compressed": DocumentMimeCategory.ARCHIVE,
    "application/msword": DocumentMimeCategory.BLOCKED,
    "application/vnd.ms-excel": DocumentMimeCategory.BLOCKED,
}

MIME_SIGNATURES: dict[bytes, str] = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    b"\x89PNG": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"RIFF": "image/webp",
    b"\xd7\xcd\xc6\x9a": "image/tiff",
    b"II*\x00": "image/tiff",
    b"MM\x00*": "image/tiff",
}

BLOCKED_EXTENSIONS: set[str] = {
    ".exe", ".bat", ".cmd", ".com", ".msi", ".dll", ".scr", ".pif",
    ".vbs", ".jse", ".wsf", ".wsh", ".ps1", ".psm1", ".sh", ".bash",
    ".jar", ".class", ".so", ".dylib",
}

MAX_ARCHIVE_SIZE_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_FILES = 1000
MAX_ARCHIVE_DEPTH = 3


class MimeDetectionService:
    """Server-side MIME type detection using magic bytes."""

    def detect_from_content(self, data: bytes) -> tuple[str, DocumentMimeCategory]:
        """Detect MIME type from file content using magic bytes."""
        detected = self._detect_from_bytes(data)
        if detected:
            category = ALLOWED_MIME_TYPES.get(detected, DocumentMimeCategory.UNKNOWN)
            return detected, category
        return "application/octet-stream", DocumentMimeCategory.UNKNOWN

    def _detect_from_bytes(self, data: bytes) -> str | None:
        """Detect MIME type from magic bytes."""
        if len(data) < 12:
            return None
        for magic, mime_type in MIME_SIGNATURES.items():
            if data.startswith(magic):
                if magic == b"RIFF" and len(data) >= 12:
                    if data[8:12] != b"WEBP":
                        continue
                return mime_type
        return None

    def validate_extension(self, filename: str) -> tuple[bool, str | None]:
        """Validate file extension."""
        import os
        _, ext = os.path.splitext(filename.lower())
        if ext in BLOCKED_EXTENSIONS:
            return False, f"File extension {ext} is not allowed for security reasons"
        return True, None

    def validate_zip_content(self, archive_info: dict) -> tuple[bool, str | None]:
        """Validate ZIP archive content."""
        total_size = archive_info.get("total_size", 0)
        file_count = archive_info.get("file_count", 0)
        max_depth = archive_info.get("max_depth", 0)

        if total_size > MAX_ARCHIVE_SIZE_BYTES:
            return False, "Archive total size exceeds limit"
        if file_count > MAX_ARCHIVE_FILES:
            return False, "Archive contains too many files"
        if max_depth > MAX_ARCHIVE_DEPTH:
            return False, "Archive nesting depth exceeds limit"
        return True, None

    def is_supported(self, mime_category: DocumentMimeCategory) -> bool:
        """Check if MIME category is supported for parsing."""
        return mime_category in {
            DocumentMimeCategory.PDF,
            DocumentMimeCategory.DOCX,
            DocumentMimeCategory.XLSX,
            DocumentMimeCategory.IMAGE,
        }

    def is_allowed(self, mime_category: DocumentMimeCategory) -> bool:
        """Check if MIME category is allowed for upload."""
        return mime_category != DocumentMimeCategory.BLOCKED
