"""Map member-4 domain reasons onto the frozen platform error catalog."""

from __future__ import annotations

from biaice.core.errors import BiaiceError

# Member-1 owns ERROR_CATALOG. Until FR-03/04 codes are registered, keep the
# domain token in detail and raise an existing stable code with the same class
# of HTTP status (conflict / not usable / already final).
_DOMAIN_TO_STABLE = {
    "EVIDENCE_DOCUMENT_NOT_RELEASED": "DOCUMENT_NOT_DOWNLOADABLE",
    "EVIDENCE_SATISFIED_WITHOUT_PROOF": "WAIVER_PROHIBITED",
    "EVIDENCE_REVIEW_REQUIRED": "MAKER_CHECKER_REQUIRED",
    "PUBLISHED_VERSION_IMMUTABLE": "DOCUMENT_ALREADY_RELEASED",
    "REQUIREMENT_NOT_PUBLISHED": "DOCUMENT_NOT_RELEASABLE",
    "RESPONSE_PROFILE_EVIDENCE_NOT_CURRENT": "RETENTION_EXPIRED",
    "CONDITION_NOT_OPEN": "JOB_NOT_CANCELLABLE",
    "COST_ALREADY_APPROVED": "DOCUMENT_ALREADY_RELEASED",
    "COST_NOT_APPROVED": "DOCUMENT_NOT_RELEASABLE",
}


def m4_error(code: str, *, detail: str | None = None) -> BiaiceError:
    return BiaiceError(_DOMAIN_TO_STABLE.get(code, code), detail=detail or code)
