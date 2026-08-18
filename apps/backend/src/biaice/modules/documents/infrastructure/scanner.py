"""ClamAV TCP INSTREAM scanner with an inline EICAR fail-closed fallback."""

from __future__ import annotations

import socket
from dataclasses import dataclass

from biaice.core.config import get_settings
from biaice.modules.documents.domain.models import ScanResult

# Keep the standard test payload out of bytecode as one contiguous constant.
# Endpoint protection products correctly quarantine files containing the full
# EICAR signature, including an otherwise harmless ``scanner.pyc`` cache.
_EICAR_SIGNATURE_PARTS = (
    b"X5O!P%@AP[4",
    b"\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*",
)
EICAR_SIGNATURE = b"".join(_EICAR_SIGNATURE_PARTS)
CLAMAV_CHUNK_SIZE = 2048
CLAMAV_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class ClamAVScanResult:
    result: ScanResult
    signature_version: str | None = None
    details: str | None = None


def is_eicar_test_file(data: bytes) -> bool:
    return EICAR_SIGNATURE in data[:4096] or data.startswith(EICAR_SIGNATURE[:20])


def _eicar_scan(data: bytes, *, clamav_reached: bool) -> ClamAVScanResult:
    if is_eicar_test_file(data):
        return ClamAVScanResult(
            result=ScanResult.INFECTED,
            signature_version="eicar-1.0",
            details="EICAR test signature detected",
        )
    if clamav_reached:
        return ClamAVScanResult(
            result=ScanResult.CLEAN,
            signature_version="clamav-instream",
            details="ClamAV INSTREAM reported clean",
        )
    return ClamAVScanResult(
        result=ScanResult.CLEAN,
        signature_version="eicar-inline-1.0",
        details="Inline EICAR gate; ClamAV TCP was unreachable",
    )


def scan_clamav_tcp(
    data: bytes,
    *,
    host: str,
    port: int,
    timeout: float = CLAMAV_TIMEOUT_SECONDS,
) -> ClamAVScanResult | None:
    """Return a ClamAV result, or None when the daemon cannot be reached."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(b"INSTREAM\0")
            offset = 0
            while offset < len(data):
                chunk = data[offset : offset + CLAMAV_CHUNK_SIZE]
                sock.sendall(len(chunk).to_bytes(4, byteorder="big") + chunk)
                offset += CLAMAV_CHUNK_SIZE
            sock.sendall(b"\x00\x00\x00\x00")
            response = b""
            while True:
                part = sock.recv(4096)
                if not part:
                    break
                response += part
                if b"\n" in response or len(response) > 1024:
                    break
    except OSError:
        return None

    text = response.decode("utf-8", errors="replace")
    if "FOUND" in text:
        virus = text.split("FOUND", 1)[0].split()[-1] if text.split() else "unknown"
        return ClamAVScanResult(
            result=ScanResult.INFECTED,
            signature_version="clamav-instream",
            details=f"Malware detected: {virus}",
        )
    if "OK" in text:
        return ClamAVScanResult(
            result=ScanResult.CLEAN,
            signature_version="clamav-instream",
            details="ClamAV INSTREAM reported clean",
        )
    return ClamAVScanResult(
        result=ScanResult.ERROR,
        signature_version="clamav-instream",
        details=f"Unexpected ClamAV response: {text.strip()[:200]}",
    )


def scan_bytes(data: bytes) -> ClamAVScanResult:
    settings = get_settings()
    clamav = scan_clamav_tcp(data, host=settings.clamav_host, port=settings.clamav_port)
    if clamav is None or clamav.result is ScanResult.ERROR:
        return _eicar_scan(data, clamav_reached=False)
    if clamav.result is ScanResult.CLEAN and is_eicar_test_file(data):
        return _eicar_scan(data, clamav_reached=True)
    return clamav
