"""Stdlib parsers for PDF/DOCX/XLSX/archives. Images require OCR that is not locked."""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass

from biaice.modules.documents.domain.models import (
    DocumentMimeCategory,
    ParseRetryable,
    ParseStatus,
)

WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


@dataclass(frozen=True)
class ParseOutcome:
    status: ParseStatus
    retryable: ParseRetryable | None = None
    failure_reason_code: str | None = None
    failure_detail: str | None = None
    text: str = ""
    page_count: int | None = None


def parse_document(data: bytes, mime_category: DocumentMimeCategory) -> ParseOutcome:
    if mime_category is DocumentMimeCategory.IMAGE:
        return ParseOutcome(
            status=ParseStatus.FAILED,
            retryable=ParseRetryable.NO_MANUAL_ENTRY_REQUIRED,
            failure_reason_code="OCR_ENGINE_UNAVAILABLE",
            failure_detail="PaddleOCR is not in the locked dependency set.",
        )
    if mime_category is DocumentMimeCategory.PDF:
        return _parse_pdf(data)
    if mime_category is DocumentMimeCategory.DOCX:
        return _parse_docx(data)
    if mime_category is DocumentMimeCategory.XLSX:
        return _parse_xlsx(data)
    if mime_category is DocumentMimeCategory.ARCHIVE:
        return _parse_archive(data)
    return ParseOutcome(
        status=ParseStatus.FAILED,
        retryable=ParseRetryable.NO_FORMAT_UNSUPPORTED,
        failure_reason_code="FORMAT_UNSUPPORTED",
        failure_detail=f"No parser is registered for {mime_category.value}.",
    )


def _parse_pdf(data: bytes) -> ParseOutcome:
    if b"/Encrypt" in data[:16384]:
        return ParseOutcome(
            status=ParseStatus.FAILED,
            retryable=ParseRetryable.NO_PASSWORD_PROTECTED,
            failure_reason_code="PASSWORD_PROTECTED",
            failure_detail="Encrypted PDF cannot be parsed without a password.",
        )
    blocks = re.findall(rb"BT(.*?)ET", data, flags=re.S)
    texts: list[str] = []
    for block in blocks:
        for match in re.findall(rb"\((?:\\.|[^\\)])*\)", block):
            texts.append(match[1:-1].decode("latin-1", errors="replace"))
    if not texts:
        literals = re.findall(rb"\((?:\\.|[^\\)]){3,}\)", data)
        texts = [item[1:-1].decode("latin-1", errors="replace") for item in literals]
    return ParseOutcome(
        status=ParseStatus.SUCCEEDED,
        text="\n".join(part for part in texts if part).strip(),
        page_count=max(data.count(b"/Type /Page"), 1),
    )


def _parse_docx(data: bytes) -> ParseOutcome:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        return ParseOutcome(
            status=ParseStatus.FAILED,
            retryable=ParseRetryable.NO_CORRUPT,
            failure_reason_code="CORRUPT_DOCUMENT",
            failure_detail=str(exc),
        )
    root = ET.fromstring(xml)
    texts = [node.text or "" for node in root.iter(f"{WORD_NS}t")]
    return ParseOutcome(status=ParseStatus.SUCCEEDED, text="\n".join(t for t in texts if t))


def _parse_xlsx(data: bytes) -> ParseOutcome:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            shared: list[str] = []
            if "xl/sharedStrings.xml" in names:
                shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                for item in shared_root:
                    shared.append(
                        "".join(node.text or "" for node in item.iter(f"{SHEET_NS}t"))
                    )
            lines: list[str] = []
            for name in names:
                if not name.startswith("xl/worksheets/sheet") or not name.endswith(".xml"):
                    continue
                lines.append(f"[SHEET {name}]")
                root = ET.fromstring(archive.read(name))
                for cell in root.iter(f"{SHEET_NS}c"):
                    value = cell.find(f"{SHEET_NS}v")
                    if value is None or value.text is None:
                        continue
                    if cell.attrib.get("t") == "s":
                        index = int(value.text)
                        lines.append(shared[index] if index < len(shared) else value.text)
                    else:
                        lines.append(value.text)
    except (KeyError, zipfile.BadZipFile, ET.ParseError, ValueError) as exc:
        return ParseOutcome(
            status=ParseStatus.FAILED,
            retryable=ParseRetryable.NO_CORRUPT,
            failure_reason_code="CORRUPT_DOCUMENT",
            failure_detail=str(exc),
        )
    return ParseOutcome(status=ParseStatus.SUCCEEDED, text="\n".join(lines).strip())


def _parse_archive(data: bytes) -> ParseOutcome:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            listing = "\n".join(archive.namelist())
    except zipfile.BadZipFile as exc:
        return ParseOutcome(
            status=ParseStatus.FAILED,
            retryable=ParseRetryable.NO_CORRUPT,
            failure_reason_code="CORRUPT_ARCHIVE",
            failure_detail=str(exc),
        )
    return ParseOutcome(status=ParseStatus.SUCCEEDED, text=listing, page_count=None)
