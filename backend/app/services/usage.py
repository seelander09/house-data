"""Usage tracking services for metering exports and enforcing plan limits."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..config import Settings
from ..models.usage import PlanAlert, PlanQuota, PlanSnapshot, UsageSummary


class UsageLimitError(Exception):
    """Raised when a usage event would exceed the subscribed plan limits."""


@dataclass(frozen=True)
class UsageEvent:
    """Lightweight container describing a metered event."""

    event_type: str
    payload: dict[str, Any]
    metadata: dict[str, Any]
    account_id: str | None
    user_id: str | None


class UsageService:
    """Persists usage events to SQLite for downstream billing and analytics."""

    _SCHEMA_STATEMENTS: Sequence[str] = (
        """
        CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            metadata TEXT NOT NULL,
            account_id TEXT,
            user_id TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_usage_events_type_created ON usage_events(event_type, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_usage_events_account ON usage_events(account_id, event_type);",
    )

    def __init__(self, settings: Settings) -> None:
        self._enabled = bool(settings.enable_usage_tracking)
        self._db_path = Path(settings.usage_db_path)
        self._lock = asyncio.Lock()
        self._initialised = False
        self._plan_window_days = max(1, settings.plan_window_days)
        self._plan_name = settings.plan_name
        self._plan_limits = {
            'properties.export': settings.plan_export_limit,
            'properties.lead_pack': settings.plan_lead_pack_limit,
            'properties.refresh_cache': settings.plan_refresh_limit,
        }
        if self._enabled:
            self._initialise_store()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _initialise_store(self) -> None:
        if self._initialised:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._db_path)
        try:
            for statement in self._SCHEMA_STATEMENTS:
                connection.execute(statement)
            connection.commit()
        finally:
            connection.close()
        self._apply_migrations()
        self._initialised = True

    def _apply_migrations(self) -> None:
        connection = sqlite3.connect(self._db_path)
        try:
            cursor = connection.execute("PRAGMA table_info(usage_events)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            if 'account_id' not in existing_columns:
                connection.execute("ALTER TABLE usage_events ADD COLUMN account_id TEXT")
            if 'user_id' not in existing_columns:
                connection.execute("ALTER TABLE usage_events ADD COLUMN user_id TEXT")
            connection.commit()
        finally:
            connection.close()

    async def log_event(
        self,
        event_type: str,
        *,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        account_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Persist a usage event if metering is enabled."""

        if not self._enabled:
            return

        event = UsageEvent(
            event_type=event_type,
            payload=payload or {},
            metadata=metadata or {},
            account_id=account_id,
            user_id=user_id,
        )

        async with self._lock:
            await asyncio.to_thread(self._write_event, event)

    def _write_event(self, event: UsageEvent) -> None:
        connection = sqlite3.connect(self._db_path)
        try:
            connection.execute(
                """
                INSERT INTO usage_events (event_type, payload, metadata, account_id, user_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.event_type,
                    json.dumps(event.payload, ensure_ascii=False),
                    json.dumps(event.metadata, ensure_ascii=False),
                    event.account_id,
                    event.user_id,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    async def get_summary(
        self,
        days: int = 30,
        *,
        account_id: str | None = None,
    ) -> list[UsageSummary]:
        """Aggregate usage counts by event type within the requested window."""

        if not self._enabled:
            return []

        window_days = max(1, min(days, 365))
        rows = await asyncio.to_thread(self._fetch_summary_rows, window_days, account_id)
        return [UsageSummary.model_validate(row) for row in rows]

    def _fetch_summary_rows(self, days: int, account_id: str | None) -> Iterable[dict[str, Any]]:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            window_clause = f'-{days} days'
            account_clause, params = self._account_filter(account_id)
            cursor = connection.execute(
                f"""
                SELECT
                    event_type AS event_type,
                    COUNT(*) AS count,
                    MAX(created_at) AS last_event_at
                FROM usage_events
                WHERE created_at >= datetime('now', ?)
                {account_clause}
                GROUP BY event_type
                ORDER BY event_type
                """,
                (window_clause, *params),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    async def count_events(
        self,
        event_type: str,
        days: int | None = None,
        *,
        account_id: str | None = None,
    ) -> int:
        """Return the number of events for ``event_type`` within ``days`` window."""

        if not self._enabled:
            return 0

        window_days = max(1, days or self._plan_window_days)
        return await asyncio.to_thread(self._fetch_count, event_type, window_days, account_id)

    def _fetch_count(self, event_type: str, days: int, account_id: str | None) -> int:
        connection = sqlite3.connect(self._db_path)
        try:
            window_clause = f'-{days} days'
            account_clause, params = self._account_filter(account_id)
            cursor = connection.execute(
                f"""
                SELECT COUNT(*)
                FROM usage_events
                WHERE event_type = ?
                  AND created_at >= datetime('now', ?)
                  {account_clause}
                """,
                (event_type, window_clause, *params),
            )
            result = cursor.fetchone()
            return int(result[0]) if result else 0
        finally:
            connection.close()

    async def ensure_within_plan(self, event_type: str, *, account_id: str | None = None) -> None:
        """Raise :class:`UsageLimitError` when the event would exceed plan limits."""

        limit = self._plan_limits.get(event_type)
        if not self._enabled or limit is None or limit <= 0:
            return

        current = await self.count_events(event_type, self._plan_window_days, account_id=account_id)
        if current >= limit:
            raise UsageLimitError(
                f'Plan limit reached for {event_type}: {current}/{limit} events '
                f'in the last {self._plan_window_days} days',
            )

    async def get_plan_snapshot(self, *, account_id: str | None = None) -> PlanSnapshot:
        """Return plan name with quota usage details."""

        quotas: list[PlanQuota] = []
        alerts: list[PlanAlert] = []
        for event_type, limit in self._plan_limits.items():
            if limit is None or limit <= 0:
                continue
            used = 0 if not self._enabled else await self.count_events(
                event_type,
                self._plan_window_days,
                account_id=account_id,
            )
            remaining = max(limit - used, 0)
            status = 'ok'
            if remaining <= 0:
                status = 'limit'
            elif remaining / limit <= 0.1:
                status = 'warning'

            quotas.append(
                PlanQuota(
                    event_type=event_type,
                    limit=limit,
                    used=used,
                    remaining=remaining,
                    window_days=self._plan_window_days,
                    status=status,
                )
            )

            if status != 'ok':
                level = 'Limit reached' if status == 'limit' else 'Usage warning'
                message = (
                    f'{level}: {event_type} has {remaining} of {limit} actions remaining '
                    f'in the {self._plan_window_days}-day window'
                )
                alerts.append(PlanAlert(event_type=event_type, status=status, message=message))

        return PlanSnapshot(plan_name=self._plan_name, quotas=quotas, alerts=alerts)

    @staticmethod
    def _account_filter(account_id: str | None) -> tuple[str, tuple[Any, ...]]:
        if account_id:
            return 'AND account_id = ?', (account_id,)
        return '', tuple()


def build_usage_service(settings: Settings) -> UsageService:
    """Helper for dependency configuration."""

    return UsageService(settings=settings)
