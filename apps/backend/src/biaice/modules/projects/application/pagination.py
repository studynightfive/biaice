"""Cursor pagination helper using member-1 CursorCodec. Member 2 only."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from biaice.core.auth import TenantScope
from biaice.core.errors import BiaiceError
from biaice.core.http import CursorCodec

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def clamp_limit(limit: int | None) -> int:
    value = DEFAULT_PAGE_SIZE if limit is None else int(limit)
    if value < 1:
        return 1
    return min(value, MAX_PAGE_SIZE)


def paginate(
    items: Sequence[T],
    *,
    scope: TenantScope,
    codec: CursorCodec | None,
    cursor: str | None,
    limit: int | None,
    sort_key: Callable[[T], str],
    tie_breaker: Callable[[T], str],
) -> tuple[tuple[T, ...], str | None, bool]:
    """Slice a already-sorted sequence with a signed, scope-bound cursor."""

    page_size = clamp_limit(limit)
    start_after: tuple[str, str] | None = None
    if cursor:
        if codec is None:
            raise BiaiceError(
                "INVALID_CURSOR",
                detail="Pagination cursor codec is not configured.",
            )
        payload = codec.decode(cursor, scope=scope)
        start_after = (payload.sort_key, payload.tie_breaker)

    selected: list[T] = []
    has_more = False
    for item in items:
        key = (sort_key(item), tie_breaker(item))
        if start_after is not None and key <= start_after:
            continue
        selected.append(item)
        if len(selected) > page_size:
            has_more = True
            selected.pop()
            break

    next_cursor = None
    if has_more and codec is not None and selected:
        last = selected[-1]
        next_cursor = codec.encode(
            scope=scope,
            sort_key=sort_key(last),
            tie_breaker=tie_breaker(last),
        )
    return tuple(selected), next_cursor, has_more
