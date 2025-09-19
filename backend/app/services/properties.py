from __future__ import annotations

import asyncio
import math
import statistics
import time
from datetime import date, datetime
from typing import Any, Iterable, List, Sequence

from ..clients.realie import RealieClient
from ..config import Settings
from ..models.property import (
    OwnerContact,
    Property,
    PropertyFilters,
    PropertyListResponse,
    ScoreBreakdown,
    ScoredProperty,
)


class PropertyService:
    """Provides property data with scoring, filtering, and caching."""

    EQUITY_WEIGHT = 0.45
    VALUE_GAP_WEIGHT = 0.35
    RECENCY_WEIGHT = 0.20
    RECENCY_WINDOW_DAYS = 5 * 365

    def __init__(self, client: RealieClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings
        self._cache: list[dict[str, Any]] = []
        self._cache_timestamp: float = 0.0
        self._cache_lock = asyncio.Lock()

    async def list_properties(self, filters: PropertyFilters) -> PropertyListResponse:
        raw_properties = await self._get_cached_properties()
        normalized = [self._normalize_property(p) for p in raw_properties]
        scored = self._score_properties(normalized)
        filtered = self._apply_filters(scored, filters)

        sorted_properties = sorted(filtered, key=lambda p: p.listing_score, reverse=True)
        total = len(sorted_properties)
        start = filters.offset
        end = start + filters.limit
        items = sorted_properties[start:end]

        return PropertyListResponse(items=items, total=total, limit=filters.limit, offset=filters.offset)

    async def export_properties(self, filters: PropertyFilters) -> List[ScoredProperty]:
        response = await self.list_properties(filters)
        return response.items

    async def refresh_cache(self, force: bool = False) -> None:
        await self._get_cached_properties(force_refresh=force)

    async def _get_cached_properties(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        now = time.monotonic()
        if not force_refresh and self._cache and (now - self._cache_timestamp) < self._settings.cache_ttl_seconds:
            return self._cache

        async with self._cache_lock:
            # Double-checked locking
            now = time.monotonic()
            if not force_refresh and self._cache and (now - self._cache_timestamp) < self._settings.cache_ttl_seconds:
                return self._cache

            data = await self._client.fetch_all_properties(max_records=self._settings.max_properties)
            self._cache = data
            self._cache_timestamp = time.monotonic()
            return self._cache

    def _normalize_property(self, raw: dict[str, Any]) -> Property:
        transfer_date = self._parse_date(raw.get('transferDate'))

        address = raw.get('addressFull') or raw.get('addressFormal') or raw.get('address') or raw.get('addressRaw')
        if not address and raw.get('street'):
            street_parts = [raw.get('streetNumber'), raw.get('streetDirectionPrefix'), raw.get('streetName'), raw.get('streetType'), raw.get('streetDirectionSuffix')]
            address = ' '.join(str(part) for part in street_parts if part)

        owner = OwnerContact(
            name=raw.get('ownerName'),
            address_line1=raw.get('ownerAddressLine1'),
            city=raw.get('ownerCity'),
            state=raw.get('ownerState'),
            postal_code=raw.get('ownerZipCode'),
            phone=raw.get('ownerPhone'),
            email=raw.get('ownerEmail'),
        )

        property_payload = {
            'id': raw.get('_id') or raw.get('id') or raw.get('parcelId') or address or 'unknown',
            'parcel_id': raw.get('parcelId'),
            'address': address,
            'city': raw.get('city'),
            'state': raw.get('state'),
            'postal_code': raw.get('zipCode') or raw.get('zipCodePlusFour'),
            'neighborhood': raw.get('neighborhood'),
            'latitude': raw.get('latitude'),
            'longitude': raw.get('longitude'),
            'total_assessed_value': self._to_float(raw.get('totalAssessedValue')),
            'total_market_value': self._to_float(raw.get('totalMarketValue')),
            'model_value': self._to_float(raw.get('modelValue')),
            'equity_current_est_bal': self._to_float(raw.get('equityCurrentEstBal')),
            'equity_available': self._to_float(raw.get('equityCurrentEstBal')),
            'transfer_date': transfer_date,
            'owner': owner,
        }

        return Property(**property_payload)

    def _score_properties(self, properties: Sequence[Property]) -> list[ScoredProperty]:
        equity_values = [p.equity_available for p in properties if p.equity_available is not None]
        equity_fallback = statistics.median(equity_values) if equity_values else 0.0
        equity_min, equity_max = self._min_max(equity_values, default=equity_fallback)

        value_gap_values = [self._value_gap(p) for p in properties if self._value_gap(p) is not None]
        value_gap_fallback = statistics.median(value_gap_values) if value_gap_values else 0.0
        value_gap_min, value_gap_max = self._min_max(value_gap_values, default=value_gap_fallback)

        scored: list[ScoredProperty] = []
        for prop in properties:
            equity_amount = prop.equity_available if prop.equity_available is not None else equity_fallback
            equity_score = self._normalise(equity_amount, equity_min, equity_max)

            value_gap = self._value_gap(prop)
            if value_gap is None:
                value_gap = value_gap_fallback
            value_gap_score = self._normalise(value_gap, value_gap_min, value_gap_max)

            recency_score = self._recency_score(prop.transfer_date)

            listing_score = (
                equity_score * self.EQUITY_WEIGHT
                + value_gap_score * self.VALUE_GAP_WEIGHT
                + recency_score * self.RECENCY_WEIGHT
            )

            scored.append(
                ScoredProperty(
                    **prop.model_dump(by_alias=True),
                    listing_score=round(listing_score * 100, 2),
                    score_breakdown=ScoreBreakdown(
                        equity=round(equity_score, 4),
                        value_gap=round(value_gap_score, 4),
                        recency=round(recency_score, 4),
                    ),
                )
            )

        return scored

    def _apply_filters(self, properties: Iterable[ScoredProperty], filters: PropertyFilters) -> list[ScoredProperty]:
        def matches(prop: ScoredProperty) -> bool:
            if filters.city and (prop.city or '').lower() != filters.city.lower():
                return False
            if filters.state and (prop.state or '').lower() != filters.state.lower():
                return False
            if filters.min_equity is not None:
                equity = prop.equity_available or 0.0
                if equity < filters.min_equity:
                    return False
            if filters.min_score is not None and prop.listing_score < filters.min_score:
                return False
            if filters.search:
                needle = filters.search.lower()
                haystacks = [
                    prop.address or '',
                    prop.city or '',
                    prop.state or '',
                    prop.owner.name or '',
                ]
                if not any(needle in (haystack.lower()) for haystack in haystacks):
                    return False
            return True

        return [prop for prop in properties if matches(prop)]

    @staticmethod
    def _value_gap(prop: Property) -> float | None:
        market = prop.model_value or prop.total_market_value
        assessed = prop.total_assessed_value
        if market is None or assessed is None:
            return None
        return max(market - assessed, 0.0)

    @classmethod
    def _recency_score(cls, transfer_date: date | None) -> float:
        if transfer_date is None:
            return 0.4  # neutral fallback when no transfer history
        days_since = (date.today() - transfer_date).days
        if days_since < 0:
            return 1.0
        if days_since >= cls.RECENCY_WINDOW_DAYS:
            return 0.0
        return 1.0 - (days_since / cls.RECENCY_WINDOW_DAYS)

    @staticmethod
    def _min_max(values: Sequence[float], default: float) -> tuple[float, float]:
        if not values:
            return default, default
        return min(values), max(values)

    @staticmethod
    def _normalise(value: float, min_value: float, max_value: float) -> float:
        if math.isclose(max_value, min_value):
            return 1.0
        return max(0.0, min(1.0, (value - min_value) / (max_value - min_value)))

    @staticmethod
    def _parse_date(raw: Any) -> date | None:
        if raw in (None, '', '00000000'):
            return None
        try:
            if isinstance(raw, (int, float)):
                raw = str(int(raw))
            raw_str = str(raw)
            if len(raw_str) == 8 and raw_str.isdigit():
                return datetime.strptime(raw_str, '%Y%m%d').date()
            return datetime.fromisoformat(raw_str).date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value in (None, ''):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
