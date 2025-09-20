from __future__ import annotations

from datetime import date, datetime
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
    value_gap: Optional[float] = None
    transfer_date: Optional[date] = None
    owner: OwnerContact = Field(default_factory=OwnerContact)
    owner_occupancy: Optional[str] = Field(default=None, description='owner_occupied or absentee')
    distance_from_search_center_miles: Optional[float] = None


class ScoredProperty(Property):
    listing_score: float
    score_breakdown: ScoreBreakdown


class PropertyListResponse(BaseModel):
    items: list[ScoredProperty]
    total: int
    limit: int
    offset: int


class LeadPack(BaseModel):
    label: str
    total: int
    top_properties: list[ScoredProperty]


class LeadPackResponse(BaseModel):
    generated_at: datetime
    packs: list[LeadPack]


class PropertyFilters(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    min_equity: Optional[float] = None
    min_score: Optional[float] = None
    min_value_gap: Optional[float] = None
    min_market_value: Optional[float] = None
    max_market_value: Optional[float] = None
    min_assessed_value: Optional[float] = None
    max_assessed_value: Optional[float] = None
    owner_occupancy: Optional[str] = None
    center_latitude: Optional[float] = None
    center_longitude: Optional[float] = None
    radius_miles: Optional[float] = None
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0

    @field_validator('search', 'city', 'state', 'postal_code', mode='before')
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator('owner_occupancy', mode='before')
    @classmethod
    def validate_owner_occupancy(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        label = value.strip().lower()
        if label in {'owner', 'owner_occupied', 'owner-occupied'}:
            return 'owner_occupied'
        if label in {'absentee', 'investor', 'non_owner'}:
            return 'absentee'
        raise ValueError(f"Unsupported owner_occupancy value '{value}'")

    @field_validator('radius_miles', mode='before')
    @classmethod
    def clamp_radius(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return value
        try:
            radius = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError('radius_miles must be numeric') from exc
        if radius <= 0:
            raise ValueError('radius_miles must be > 0')
        return radius

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

    def requires_radius_filter(self) -> bool:
        return self.radius_miles is not None

    def has_radius_coordinates(self) -> bool:
        return self.center_latitude is not None and self.center_longitude is not None

    def normalize_for_radius(self) -> None:
        if self.requires_radius_filter() and not self.has_radius_coordinates():
            raise ValueError('center_latitude and center_longitude are required with radius_miles')
