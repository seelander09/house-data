from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class OwnerContact(BaseModel):
    name: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ScoreBreakdown(BaseModel):
    equity: float
    value_gap: float
    recency: float


class Property(BaseModel):
    property_id: str = Field(alias='id')
    parcel_id: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    neighborhood: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_assessed_value: Optional[float] = None
    total_market_value: Optional[float] = None
    model_value: Optional[float] = None
    equity_current_est_bal: Optional[float] = None
    equity_available: Optional[float] = None
    transfer_date: Optional[date] = None
    owner: OwnerContact = Field(default_factory=OwnerContact)


class ScoredProperty(Property):
    listing_score: float
    score_breakdown: ScoreBreakdown


class PropertyListResponse(BaseModel):
    items: list[ScoredProperty]
    total: int
    limit: int
    offset: int


class PropertyFilters(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    min_equity: Optional[float] = None
    min_score: Optional[float] = None
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0

    @field_validator('search', 'city', 'state')
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator('limit', mode='before')
    @classmethod
    def clamp_limit(cls, value: int) -> int:
        value = value or 50
        return max(1, min(200, int(value)))

    @field_validator('offset', mode='before')
    @classmethod
    def clamp_offset(cls, value: int) -> int:
        value = value or 0
        return max(0, int(value))
