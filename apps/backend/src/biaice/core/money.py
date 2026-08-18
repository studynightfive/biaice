"""Exact money type shared by all business modules."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class Money(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    amount: Decimal = Field(description="Decimal fixed-point value, serialized as a string")
    currency: str = Field(pattern=r"^[A-Z]{3}$", description="ISO 4217 currency code")

    @field_validator("amount", mode="before")
    @classmethod
    def reject_binary_float(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("binary floating point is forbidden for formal money")
        return value

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return format(value, "f")
