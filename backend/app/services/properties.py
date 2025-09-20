from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import math
import statistics
import time
from datetime import date, datetime, timezone
from typing import Any, Iterable, List, Sequence

from ..clients.realie import RealieClient
from ..config import Settings
from ..models.property import (
    LeadPack,
    LeadPackResponse,
    Property,
    PropertyFilters,
    PropertyListResponse,
    ScoreBreakdown,
    ScoredProperty,
)

try:  # pragma: no cover - optional dependency
    import redis.asyncio as redis  # type: ignore
except ImportError:  # pragma: no cover - redis optional
    redis = None

logger = logging.getLogger(__name__)


class PropertyService:
    """Provides property data with scoring, filtering, and caching."""

    RECENCY_WINDOW_DAYS = 5 * 365

    def __init__(self, client: RealieClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings
        self._cache: list[dict[str, Any]] = []
        self._cache_timestamp: float = 0.0
        self._cache_lock = asyncio.Lock()

        self._weights = self._normalise_weights(
            settings.scoring_equity_weight,
            settings.scoring_value_gap_weight,
            settings.scoring_recency_weight,
        )
        logger.info("Scoring weights normalised to equity=%s value_gap=%s recency=%s",
                     self._weights['equity'],
                     self._weights['value_gap'],
                     self._weights['recency'])


        self._cache_backend = settings.cache_backend.lower()
        self._cache_namespace = settings.cache_namespace
        self._cache_key = f"{self._cache_namespace}:properties"
        self._redis_client = self._initialise_redis(settings)

        self._refresh_interval = max(60, int(settings.refresh_interval_seconds))
        self._scheduler_enabled = bool(settings.enable_scheduler)
        self._refresh_task: asyncio.Task[None] | None = None

    @property
    def max_properties(self) -> int:
        return self._settings.max_properties

    async def list_properties(self, filters: PropertyFilters) -> PropertyListResponse:
        filters.normalize_for_radius()
        raw_properties = await self._get_cached_properties()
        normalized = [self._normalize_property(p) for p in raw_properties]
        scored = self._score_properties(normalized)
        filtered = self._apply_filters(scored, filters)

        sorted_properties = sorted(filtered, key=lambda p: p.listing_score, reverse=True)
        self._log_scoring_snapshot(sorted_properties)

        total = len(sorted_properties)
        start = filters.offset
        end = start + filters.limit
        items = sorted_properties[start:end]

        return PropertyListResponse(items=items, total=total, limit=filters.limit, offset=filters.offset)

    async def export_properties(self, filters: PropertyFilters) -> List[ScoredProperty]:
        response = await self.list_properties(filters)
        return response.items

    async def generate_lead_packs(
        self,
        filters: PropertyFilters,
        group_by: str = 'postal_code',
        pack_size: int = 200,
    ) -> LeadPackResponse:
        group_attr = {
            'postal_code': 'postal_code',
            'zip': 'postal_code',
            'zip_code': 'postal_code',
            'city': 'city',
            'state': 'state',
        }.get(group_by.lower(), group_by)

        working_filters = filters.model_copy()
        working_filters.limit = max(filters.limit, self.max_properties)
        working_filters.offset = 0
        working_filters.normalize_for_radius()

        response = await self.list_properties(working_filters)

        buckets: dict[str, list[ScoredProperty]] = {}
        for item in response.items:
            label = getattr(item, group_attr, None) or 'unclassified'
            buckets.setdefault(label, []).append(item)

        packs: list[LeadPack] = []
        for label, items in buckets.items():
            ordered = sorted(items, key=lambda p: p.listing_score, reverse=True)[:pack_size]
            packs.append(
                LeadPack(
                    label=str(label),
                    total=len(items),
                    top_properties=ordered,
                )
            )

        packs.sort(key=lambda pack: pack.top_properties[0].listing_score if pack.top_properties else 0, reverse=True)
        return LeadPackResponse(generated_at=datetime.now(timezone.utc), packs=packs)

    async def refresh_cache(self, force: bool = False) -> None:
        await self._get_cached_properties(force_refresh=force)

    def spawn_refresh_task(self) -> asyncio.Task[None] | None:
        if not self._scheduler_enabled:
            logger.debug('Scheduler disabled; skipping background refresh task')
            return None
        if self._refresh_task and not self._refresh_task.done():
            return self._refresh_task
        self._refresh_task = asyncio.create_task(self._refresh_loop(), name='property-cache-refresh')
        return self._refresh_task

    async def shutdown_refresh_task(self) -> None:
        if not self._refresh_task:
            return
        task = self._refresh_task
        self._refresh_task = None
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _refresh_loop(self) -> None:
        logger.info('Starting property cache refresh loop (interval=%ss)', self._refresh_interval)
        try:
            while True:
                try:
                    await self.refresh_cache(force=True)
                    logger.debug('Property cache refresh complete')
                except Exception:  # pragma: no cover - defensive logging
                    logger.exception('Property cache refresh failed')
                await asyncio.sleep(self._refresh_interval)
        except asyncio.CancelledError:  # pragma: no cover - cancellation path
            logger.info('Stopping property cache refresh loop')
            raise

    def _initialise_redis(self, settings: Settings):
        if self._cache_backend != 'redis':
            return None
        if not settings.redis_url:
            logger.warning('CACHE_BACKEND=redis but REDIS_URL is not configured; falling back to memory cache')
            return None
        if redis is None:
            logger.warning('redis package not installed; falling back to memory cache')
            return None
        client = redis.from_url(settings.redis_url, encoding='utf-8', decode_responses=True)
        logger.info('Redis cache enabled (namespace=%s)', self._cache_namespace)
        return client

    async def _get_cached_properties(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        now = time.monotonic()
        if not force_refresh and self._cache and (now - self._cache_timestamp) < self._settings.cache_ttl_seconds:
            return self._cache

        async with self._cache_lock:
            now = time.monotonic()
            if not force_refresh and self._cache and (now - self._cache_timestamp) < self._settings.cache_ttl_seconds:
                return self._cache

            if not force_refresh and self._redis_client:
                cached = await self._load_from_redis()
                if cached is not None:
                    self._cache = cached
                    self._cache_timestamp = time.monotonic()
                    logger.debug('Loaded %s properties from redis cache', len(cached))
                    return self._cache

            data = await self._client.fetch_all_properties(max_records=self.max_properties)
            self._cache = data
            self._cache_timestamp = time.monotonic()
            if self._redis_client:
                await self._store_in_redis(data)
            logger.debug('Fetched %s properties from Realie API', len(data))
            return self._cache

    async def _load_from_redis(self) -> list[dict[str, Any]] | None:
        if not self._redis_client:
            return None
        try:
            payload = await self._redis_client.get(self._cache_key)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception('Unable to read property cache from redis')
            return None
        if not payload:
            return None
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning('Invalid JSON payload in redis cache; ignoring')
            return None
        if isinstance(data, list):
            return data
        logger.warning('Unexpected redis cache payload type %s', type(data))
        return None

    async def _store_in_redis(self, data: list[dict[str, Any]]) -> None:
        if not self._redis_client:
            return
        try:
            await self._redis_client.set(
                self._cache_key,
                json.dumps(data),
                ex=int(self._settings.cache_ttl_seconds * 2),
            )
        except Exception:  # pragma: no cover - defensive logging
            logger.exception('Failed to persist property cache to redis')

    def _normalize_property(self, raw: dict[str, Any]) -> Property:
        transfer_date = self._parse_date(raw.get('transferDate'))

        address = (
            raw.get('addressFull')
            or raw.get('addressFormal')
            or raw.get('address')
            or raw.get('addressRaw')
        )
        if not address and raw.get('street'):
            street_parts = [
                raw.get('streetNumber'),
                raw.get('streetDirectionPrefix'),
                raw.get('streetName'),
                raw.get('streetType'),
                raw.get('streetDirectionSuffix'),
            ]
            address = ' '.join(str(part) for part in street_parts if part)

        owner = self._build_owner_contact(raw)

        property_payload = {
            'id': raw.get('_id') or raw.get('id') or raw.get('parcelId') or address or 'unknown',
            'parcel_id': raw.get('parcelId'),
            'address': address,
            'city': raw.get('city'),
            'state': raw.get('state'),
            'postal_code': raw.get('zipCode') or raw.get('zipCodePlusFour'),
            'neighborhood': raw.get('neighborhood'),
            'latitude': self._to_float(raw.get('latitude')),
            'longitude': self._to_float(raw.get('longitude')),
            'total_assessed_value': self._to_float(raw.get('totalAssessedValue')),
            'total_market_value': self._to_float(raw.get('totalMarketValue')),
            'model_value': self._to_float(raw.get('modelValue')),
            'equity_current_est_bal': self._to_float(self._first_non_null(raw, 'equityCurrentEstBal', 'equityCurrentBalance')),
            'equity_available': self._to_float(self._first_non_null(raw, 'equityAvailable', 'availableEquity', 'equityCurrentEstBal')),
            'value_gap': None,
            'transfer_date': transfer_date,
            'owner': owner,
        }

        prop = Property(**property_payload)
        prop.value_gap = self._value_gap(prop)
        prop.owner_occupancy = self._derive_owner_occupancy(prop)
        return prop

    def _score_properties(self, properties: Sequence[Property]) -> list[ScoredProperty]:
        equity_values = [p.equity_available for p in properties if p.equity_available is not None]
        equity_fallback = statistics.median(equity_values) if equity_values else 0.0
        equity_min, equity_max = self._min_max(equity_values, default=equity_fallback)

        value_gap_values = [p.value_gap for p in properties if p.value_gap is not None]
        value_gap_fallback = statistics.median(value_gap_values) if value_gap_values else 0.0
        value_gap_min, value_gap_max = self._min_max(value_gap_values, default=value_gap_fallback)

        scored: list[ScoredProperty] = []
        for prop in properties:
            equity_amount = prop.equity_available if prop.equity_available is not None else equity_fallback
            equity_score = self._normalise(equity_amount, equity_min, equity_max)

            value_gap = prop.value_gap if prop.value_gap is not None else value_gap_fallback
            value_gap_score = self._normalise(value_gap, value_gap_min, value_gap_max)

            recency_score = self._recency_score(prop.transfer_date)

            listing_score = (
                equity_score * self._weights['equity']
                + value_gap_score * self._weights['value_gap']
                + recency_score * self._weights['recency']
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
            if filters.city and not self._contains(prop.city, filters.city):
                return False
            if filters.state and not self._starts_with(prop.state, filters.state):
                return False
            if filters.postal_code and not self._starts_with(prop.postal_code, filters.postal_code):
                return False
            if filters.owner_occupancy and prop.owner_occupancy != filters.owner_occupancy:
                return False
            if filters.min_equity is not None:
                equity = prop.equity_available or 0.0
                if equity < filters.min_equity:
                    return False
            if filters.min_value_gap is not None:
                gap = prop.value_gap or 0.0
                if gap < filters.min_value_gap:
                    return False
            if filters.min_market_value is not None or filters.max_market_value is not None:
                market_value = prop.total_market_value or prop.model_value or 0.0
                if filters.min_market_value is not None and (market_value or 0.0) < filters.min_market_value:
                    return False
                if filters.max_market_value is not None and market_value > filters.max_market_value:
                    return False
            if filters.min_assessed_value is not None or filters.max_assessed_value is not None:
                assessed = prop.total_assessed_value or 0.0
                if filters.min_assessed_value is not None and assessed < filters.min_assessed_value:
                    return False
                if filters.max_assessed_value is not None and assessed > filters.max_assessed_value:
                    return False
            if filters.min_score is not None and prop.listing_score < filters.min_score:
                return False
            if filters.requires_radius_filter():
                if prop.latitude is None or prop.longitude is None:
                    return False
                distance = self._haversine_distance(
                    filters.center_latitude,
                    filters.center_longitude,
                    prop.latitude,
                    prop.longitude,
                )
                prop.distance_from_search_center_miles = distance
                if filters.radius_miles is not None and distance > filters.radius_miles:
                    return False
            else:
                prop.distance_from_search_center_miles = None
            if filters.search:
                needle = filters.search.lower()
                haystacks = [
                    prop.address or '',
                    prop.city or '',
                    prop.state or '',
                    prop.owner.name or '',
                    prop.owner.address_line1 or '',
                    prop.owner.phone or '',
                    prop.owner.email or '',
                    prop.property_id,
                    prop.parcel_id or '',
                ]
                if not any(needle in hay.lower() for hay in haystacks):
                    return False
            return True

        filtered = [prop for prop in properties if matches(prop)]
        return filtered

    def _derive_owner_occupancy(self, prop: Property) -> str | None:
        property_tuple = (
            (prop.address or '').strip().lower(),
            (prop.city or '').strip().lower(),
            (prop.state or '').strip().lower(),
            (prop.postal_code or '').strip().lower(),
        )
        owner = prop.owner
        owner_tuple = (
            (owner.address_line1 or '').strip().lower(),
            (owner.city or '').strip().lower(),
            (owner.state or '').strip().lower(),
            (owner.postal_code or '').strip().lower(),
        )
        if all(property_tuple) and all(owner_tuple):
            if property_tuple == owner_tuple:
                return 'owner_occupied'
            return 'absentee'
        return None

    def _log_scoring_snapshot(self, properties: Sequence[ScoredProperty]) -> None:
        if not logger.isEnabledFor(logging.DEBUG):
            return
        sample = properties[:5]
        for prop in sample:
            logger.debug(
                'Score breakdown for %s: score=%s breakdown=%s',
                prop.property_id,
                prop.listing_score,
                prop.score_breakdown,
            )

    @staticmethod
    def _build_owner_contact(raw: dict[str, Any]):
        from ..models.property import OwnerContact

        return OwnerContact(
            name=raw.get('ownerName') or raw.get('owner1FullName'),
            address_line1=raw.get('ownerAddressLine1') or raw.get('ownerMailingAddress'),
            city=raw.get('ownerCity'),
            state=raw.get('ownerState'),
            postal_code=raw.get('ownerZipCode'),
            phone=raw.get('ownerPhone'),
            email=raw.get('ownerEmail'),
        )

    @staticmethod
    def _first_non_null(raw: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = raw.get(key)
            if value not in (None, ''):
                return value
        return None

    @staticmethod
    def _value_gap(prop: Property) -> float | None:
        market = prop.model_value or prop.total_market_value
        assessed = prop.total_assessed_value
        if market is None or assessed is None:
            return None
        return max(market - assessed, 0.0)

    def _recency_score(self, transfer_date: date | None) -> float:
        if transfer_date is None:
            return 0.4  # neutral fallback
        days_since = (date.today() - transfer_date).days
        if days_since < 0:
            return 1.0
        if days_since >= self.RECENCY_WINDOW_DAYS:
            return 0.0
        return 1.0 - (days_since / self.RECENCY_WINDOW_DAYS)

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

    @staticmethod
    def _contains(value: str | None, query: str) -> bool:
        if not value:
            return False
        return query.lower() in value.lower()

    @staticmethod
    def _starts_with(value: str | None, query: str) -> bool:
        if not value:
            return False
        return value.lower().startswith(query.lower())

    @staticmethod
    def _haversine_distance(lat1: float | None, lon1: float | None, lat2: float, lon2: float) -> float:
        if lat1 is None or lon1 is None:
            return math.inf
        radius_earth_miles = 3958.8
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        return radius_earth_miles * c

    @staticmethod
    def _normalise_weights(equity: float, value_gap: float, recency: float) -> dict[str, float]:
        weights = {
            'equity': max(equity, 0.0),
            'value_gap': max(value_gap, 0.0),
            'recency': max(recency, 0.0),
        }
        total = sum(weights.values()) or 1.0
        return {key: round(w / total, 4) for key, w in weights.items()}
