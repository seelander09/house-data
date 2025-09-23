"""Usage tracking services for metering, analytics, and plan management."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import httpx

from ..config import Settings
from ..models.usage import (
    PlanAlert,
    PlanDefinition,
    PlanQuota,
    PlanSnapshot,
    UsageAlertRecord,
    UsageHistoryEntry,
    UsageSummary,
)

logger = logging.getLogger(__name__)

_DEFAULT_PLAN_CATALOG = {
    'starter': {
        'display_name': 'Starter',
        'description': 'For solo agents exploring new markets.',
        'price': '$79/mo',
        'limits': {
            'properties.export': 150,
            'properties.lead_pack': 40,
            'properties.refresh_cache': 20,
        },
    },
    'growth': {
        'display_name': 'Growth',
        'description': 'Balanced tier for busy teams with regular campaigns.',
        'price': '$149/mo',
        'limits': {
            'properties.export': 500,
            'properties.lead_pack': 120,
            'properties.refresh_cache': 60,
        },
    },
    'scale': {
        'display_name': 'Scale',
        'description': 'High-volume quota with priority refresh cadence.',
        'price': '$349/mo',
        'limits': {
            'properties.export': 2000,
            'properties.lead_pack': 480,
            'properties.refresh_cache': 240,
        },
    },
}

_GLOBAL_ACCOUNT = '__global__'


class UsageLimitError(Exception):
    """Raised when a usage event would exceed the subscribed plan limits."""


@dataclass(frozen=True)
class UsageEvent:
    """Lightweight container describing a metered event."""

    event_type: str
    payload: dict[str, Any]
    metadata: dict[str, Any]
    account_id: str
    user_id: str | None


@dataclass(frozen=True)
class UsageAlertPayload:
    """Alert payload for dispatchers."""

    account_id: str
    plan_name: str
    event_type: str
    status: str
    message: str


class AlertDispatcher:
    """Dispatches usage alerts to optional webhook and logs."""

    def __init__(self, webhook_url: str | None, email: str | None) -> None:
        self._webhook_url = webhook_url
        self._email = email

    async def dispatch(self, alert: UsageAlertPayload) -> None:
        tasks: list[asyncio.Future[Any] | asyncio.Task[Any]] = []
        if self._webhook_url:
            tasks.append(asyncio.create_task(self._post_webhook(alert)))
        if self._email:
            logger.info(
                'Usage alert for %s (%s) -> %s: %s',
                alert.account_id,
                alert.plan_name,
                self._email,
                alert.message,
            )
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _post_webhook(self, alert: UsageAlertPayload) -> None:
        payload = {
            'account_id': alert.account_id,
            'plan': alert.plan_name,
            'event_type': alert.event_type,
            'status': alert.status,
            'message': alert.message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self._webhook_url, json=payload)
            response.raise_for_status()
        except Exception:  # pragma: no cover - defensive logging
            logger.exception('Failed to POST usage webhook for %s', alert.account_id)


class UsageService:
    """Provides usage tracking, quota enforcement, analytics, and plan management."""

    _SCHEMA_STATEMENTS: Sequence[str] = (
        """
        CREATE TABLE IF NOT EXISTS usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            metadata TEXT NOT NULL,
            account_id TEXT NOT NULL,
            user_id TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_usage_events_type_created ON usage_events(event_type, created_at);",
        "CREATE INDEX IF NOT EXISTS idx_usage_events_account ON usage_events(account_id, event_type);",
        """
        CREATE TABLE IF NOT EXISTS plan_subscriptions (
            account_id TEXT PRIMARY KEY,
            plan_name TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS usage_alert_state (
            account_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            last_sent_at TIMESTAMP,
            PRIMARY KEY (account_id, event_type)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS usage_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT NOT NULL,
            metadata TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "CREATE INDEX IF NOT EXISTS idx_usage_alerts_account ON usage_alerts(account_id, created_at DESC);",
    )
    def __init__(self, settings: Settings) -> None:
        self._enabled = bool(settings.enable_usage_tracking)
        self._db_path = Path(settings.usage_db_path)
        self._lock = asyncio.Lock()
        self._alert_dispatcher = AlertDispatcher(settings.alert_webhook_url, settings.alert_email)
        self._alert_min_interval = timedelta(minutes=max(1, settings.alert_min_interval_minutes))
        self._plan_window_days = max(1, settings.plan_window_days)
        self._plan_catalog = self._load_plan_catalog(settings.plan_catalog_json)
        if settings.plan_name not in self._plan_catalog:
            raise ValueError(f"PLAN_NAME '{settings.plan_name}' missing from plan catalog")
        self._default_plan_name = settings.plan_name
        default_plan = self._plan_catalog[self._default_plan_name]
        tuned_limits = dict(default_plan.limits)
        tuned_limits.update(
            {
                'properties.export': settings.plan_export_limit,
                'properties.lead_pack': settings.plan_lead_pack_limit,
                'properties.refresh_cache': settings.plan_refresh_limit,
            }
        )
        self._plan_catalog[self._default_plan_name] = PlanDefinition(
            name=default_plan.name,
            display_name=default_plan.display_name,
            description=default_plan.description,
            price=default_plan.price,
            limits=tuned_limits,
        )
        self._default_plan = self._plan_catalog[self._default_plan_name]
        if self._enabled:
            self._initialise_store()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _initialise_store(self) -> None:
        if self._db_path.parent and not self._db_path.parent.exists():
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._db_path)
        try:
            for statement in self._SCHEMA_STATEMENTS:
                connection.execute(statement)
            connection.commit()
            self._apply_migrations(connection)
        finally:
            connection.close()

    def _apply_migrations(self, connection: sqlite3.Connection) -> None:
        cursor = connection.execute("PRAGMA table_info(usage_events)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if 'account_id' not in existing_columns:
            connection.execute(
                "ALTER TABLE usage_events ADD COLUMN account_id TEXT NOT NULL DEFAULT '__global__'"
            )
        if 'user_id' not in existing_columns:
            connection.execute("ALTER TABLE usage_events ADD COLUMN user_id TEXT")
        connection.execute(
            "UPDATE usage_events SET account_id = ? WHERE account_id IS NULL",
            (_GLOBAL_ACCOUNT,),
        )
        connection.commit()

    def _load_plan_catalog(self, catalog_json: str | None) -> dict[str, PlanDefinition]:
        if catalog_json:
            try:
                payload = json.loads(catalog_json)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise ValueError('PLAN_CATALOG_JSON must be valid JSON') from exc
        else:
            payload = _DEFAULT_PLAN_CATALOG
        catalog: dict[str, PlanDefinition] = {}
        for name, data in payload.items():
            catalog[name] = PlanDefinition(
                name=name,
                display_name=data.get('display_name', name.title()),
                description=data.get('description', ''),
                price=data.get('price', ''),
                limits=data.get('limits', {}),
            )
        return catalog

    def _normalise_account_id(self, account_id: str | None) -> str:
        return account_id or _GLOBAL_ACCOUNT

    async def log_event(
        self,
        event_type: str,
        *,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        account_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        if not self._enabled:
            return
        event = UsageEvent(
            event_type=event_type,
            payload=payload or {},
            metadata=metadata or {},
            account_id=self._normalise_account_id(account_id),
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
        if not self._enabled:
            return []
        window_days = max(1, min(days, 365))
        rows = await asyncio.to_thread(
            self._fetch_summary_rows,
            window_days,
            self._normalise_account_id(account_id),
        )
        return [UsageSummary.model_validate(row) for row in rows]

    def _fetch_summary_rows(self, days: int, account_id: str) -> Iterable[dict[str, Any]]:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            window_clause = f'-{days} days'
            cursor = connection.execute(
                """
                SELECT
                    event_type AS event_type,
                    COUNT(*) AS count,
                    MAX(created_at) AS last_event_at
                FROM usage_events
                WHERE created_at >= datetime('now', ?)
                  AND account_id = ?
                GROUP BY event_type
                ORDER BY event_type
                """,
                (window_clause, account_id),
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
        if not self._enabled:
            return 0
        window_days = max(1, days or self._plan_window_days)
        return await asyncio.to_thread(
            self._fetch_count,
            event_type,
            window_days,
            self._normalise_account_id(account_id),
        )

    def _fetch_count(self, event_type: str, days: int, account_id: str) -> int:
        connection = sqlite3.connect(self._db_path)
        try:
            window_clause = f'-{days} days'
            cursor = connection.execute(
                """
                SELECT COUNT(*)
                FROM usage_events
                WHERE event_type = ?
                  AND created_at >= datetime('now', ?)
                  AND account_id = ?
                """,
                (event_type, window_clause, account_id),
            )
            result = cursor.fetchone()
            return int(result[0]) if result else 0
        finally:
            connection.close()
    async def ensure_within_plan(self, event_type: str, *, account_id: str | None = None) -> None:
        if not self._enabled:
            return
        plan = await self._plan_for_account(account_id)
        limit = plan.limits.get(event_type)
        if limit is None or limit <= 0:
            return
        current = await self.count_events(event_type, self._plan_window_days, account_id=account_id)
        if current >= limit:
            await self._record_alert(
                self._normalise_account_id(account_id),
                plan,
                event_type,
                'limit',
                remaining=0,
                limit=limit,
            )
            raise UsageLimitError(
                f'Plan limit reached for {event_type}: {current}/{limit} events '
                f'in the last {self._plan_window_days} days',
            )

    async def get_plan_snapshot(self, *, account_id: str | None = None) -> PlanSnapshot:
        plan = await self._plan_for_account(account_id)
        normalised = self._normalise_account_id(account_id)
        quotas: list[PlanQuota] = []
        alerts: list[PlanAlert] = []
        for event_type, limit in plan.limits.items():
            if limit <= 0:
                continue
            used = await self.count_events(event_type, self._plan_window_days, account_id=account_id)
            remaining = max(limit - used, 0)
            status = 'ok'
            if remaining <= 0:
                status = 'limit'
            elif remaining / limit <= 0.1:
                status = 'warning'
            quota = PlanQuota(
                event_type=event_type,
                limit=limit,
                used=used,
                remaining=remaining,
                window_days=self._plan_window_days,
                status=status,
            )
            quotas.append(quota)
            if status != 'ok':
                alert = await self._record_alert(normalised, plan, event_type, status, remaining, limit)
                if alert:
                    alerts.append(alert)
            else:
                await self._reset_alert_state(normalised, event_type)
        return PlanSnapshot(
            plan_name=plan.name,
            plan_display_name=plan.display_name,
            quotas=quotas,
            alerts=alerts,
        )

    async def get_usage_history(
        self,
        days: int = 30,
        *,
        account_id: str | None = None,
    ) -> list[UsageHistoryEntry]:
        window_days = max(1, min(days, 365))
        rows = await asyncio.to_thread(
            self._fetch_history_rows,
            window_days,
            self._normalise_account_id(account_id),
        )
        return [UsageHistoryEntry.model_validate(row) for row in rows]

    def _fetch_history_rows(self, days: int, account_id: str) -> Iterable[dict[str, Any]]:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            window_clause = f'-{days} days'
            cursor = connection.execute(
                """
                SELECT date(created_at) AS date,
                       event_type AS event_type,
                       COUNT(*) AS count
                FROM usage_events
                WHERE created_at >= datetime('now', ?)
                  AND account_id = ?
                GROUP BY date(created_at), event_type
                ORDER BY date(created_at)
                """,
                (window_clause, account_id),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    async def get_recent_alerts(self, *, account_id: str | None = None, limit: int = 20) -> list[UsageAlertRecord]:
        rows = await asyncio.to_thread(
            self._fetch_alert_rows,
            self._normalise_account_id(account_id),
            max(1, limit),
        )
        return [UsageAlertRecord.model_validate(row) for row in rows]

    def _fetch_alert_rows(self, account_id: str, limit: int) -> Iterable[dict[str, Any]]:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.execute(
                """
                SELECT event_type AS event_type,
                       status AS status,
                       message AS message,
                       account_id AS account_id,
                       created_at AS created_at
                FROM usage_alerts
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (account_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    async def get_plan_catalog(self) -> list[PlanDefinition]:
        return list(self._plan_catalog.values())

    async def set_plan_for_account(self, account_id: str, plan_name: str) -> PlanSnapshot:
        if not account_id:
            raise ValueError('account_id is required to select a plan')
        if plan_name not in self._plan_catalog:
            raise ValueError(f'Unknown plan {plan_name}')
        normalised = self._normalise_account_id(account_id)
        await asyncio.to_thread(self._store_subscription, normalised, plan_name)
        return await self.get_plan_snapshot(account_id=normalised)

    def _store_subscription(self, account_id: str, plan_name: str) -> None:
        connection = sqlite3.connect(self._db_path)
        try:
            connection.execute(
                """
                INSERT INTO plan_subscriptions (account_id, plan_name)
                VALUES (?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    plan_name = excluded.plan_name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (account_id, plan_name),
            )
            connection.commit()
        finally:
            connection.close()

    async def _plan_for_account(self, account_id: str | None) -> PlanDefinition:
        normalised = self._normalise_account_id(account_id)
        plan_name = await asyncio.to_thread(self._fetch_subscription_plan, normalised)
        if plan_name and plan_name in self._plan_catalog:
            return self._plan_catalog[plan_name]
        return self._default_plan

    def _fetch_subscription_plan(self, account_id: str) -> str | None:
        connection = sqlite3.connect(self._db_path)
        try:
            cursor = connection.execute(
                "SELECT plan_name FROM plan_subscriptions WHERE account_id = ?",
                (account_id,),
            )
            row = cursor.fetchone()
            return str(row[0]) if row else None
        finally:
            connection.close()

    async def _record_alert(
        self,
        account_id: str,
        plan: PlanDefinition,
        event_type: str,
        status: str,
        remaining: int,
        limit: int,
    ) -> PlanAlert | None:
        now = datetime.now(timezone.utc)
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.execute(
                "SELECT status, last_sent_at FROM usage_alert_state WHERE account_id = ? AND event_type = ?",
                (account_id, event_type),
            )
            row = cursor.fetchone()
            last_status = row['status'] if row else None
            last_sent_at = (
                datetime.fromisoformat(row['last_sent_at']) if row and row['last_sent_at'] else None
            )
            message = (
                f"Plan '{plan.display_name}' usage {status.upper()} for {event_type}: "
                f"{remaining} of {limit} actions remaining in {self._plan_window_days}-day window"
            )
            if last_status == status and last_sent_at and now - last_sent_at < self._alert_min_interval:
                cursor_msg = connection.execute(
                    """
                    SELECT message FROM usage_alerts
                    WHERE account_id = ? AND event_type = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (account_id, event_type),
                )
                row_msg = cursor_msg.fetchone()
                existing_message = row_msg['message'] if row_msg else message
                return PlanAlert(event_type=event_type, status=status, message=existing_message)
            connection.execute(
                """
                INSERT INTO usage_alert_state (account_id, event_type, status, last_sent_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(account_id, event_type) DO UPDATE SET
                    status = excluded.status,
                    last_sent_at = excluded.last_sent_at
                """,
                (account_id, event_type, status, now.isoformat()),
            )
            connection.execute(
                """
                INSERT INTO usage_alerts (account_id, event_type, status, message, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    event_type,
                    status,
                    message,
                    json.dumps({'remaining': remaining, 'limit': limit, 'plan': plan.name}),
                ),
            )
            connection.commit()
        finally:
            connection.close()
        await self._alert_dispatcher.dispatch(
            UsageAlertPayload(
                account_id=account_id,
                plan_name=plan.name,
                event_type=event_type,
                status=status,
                message=message,
            )
        )
        return PlanAlert(event_type=event_type, status=status, message=message)

    async def _reset_alert_state(self, account_id: str, event_type: str) -> None:
        connection = sqlite3.connect(self._db_path)
        try:
            connection.execute(
                "DELETE FROM usage_alert_state WHERE account_id = ? AND event_type = ?",
                (account_id, event_type),
            )
            connection.commit()
        finally:
            connection.close()


def build_usage_service(settings: Settings) -> UsageService:
    return UsageService(settings=settings)
