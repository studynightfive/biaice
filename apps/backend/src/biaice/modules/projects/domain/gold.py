"""Closed gold evaluators for FR-01 formula, rounding and tie expressions."""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import Mapping

_ROUNDING = {
    "half_up": ROUND_HALF_UP,
    "trunc": ROUND_DOWN,
    "half_even": ROUND_HALF_EVEN,
}


def apply_formula(expression: str, inputs: Mapping[str, Decimal]) -> Decimal:
    kind, rest = expression.split(":", 1)
    if kind != "weighted_sum":
        raise ValueError(f"unsupported gold formula: {kind}")
    total = Decimal("0")
    for part in rest.split(","):
        name, weight = part.split("=", 1)
        total += inputs[name] * Decimal(weight)
    return total


def apply_rounding(expression: str, value: Decimal) -> Decimal:
    mode, digits = expression.split(":", 1)
    rounding = _ROUNDING.get(mode)
    if rounding is None:
        raise ValueError(f"unsupported gold rounding: {mode}")
    quantum = Decimal("1").scaleb(-int(digits))
    return value.quantize(quantum, rounding=rounding)


def apply_tie(
    expression: str, rows: tuple[Mapping[str, object], ...]
) -> tuple[Mapping[str, object], ...]:
    kind, rest = expression.split(":", 1)
    if kind != "order":
        raise ValueError(f"unsupported gold tie: {kind}")
    specs: list[tuple[str, bool]] = []
    for spec in rest.split(","):
        field, direction = spec.rsplit("_", 1)
        if direction not in {"asc", "desc"}:
            raise ValueError(f"unsupported tie direction: {direction}")
        specs.append((field, direction == "desc"))

    def sort_key(row: Mapping[str, object]) -> tuple[object, ...]:
        keys: list[object] = []
        for field, reverse in specs:
            value = row[field]
            if reverse and isinstance(value, Decimal):
                keys.append(-value)
            else:
                keys.append(value)
        return tuple(keys)

    return tuple(sorted(rows, key=sort_key))
