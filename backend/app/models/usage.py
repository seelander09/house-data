from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UsageSummary(BaseModel):
    """Aggregated counts of tracked usage events."""

    event_type: str = Field(description='Identifier for the metered event (e.g. properties.export)')
    count: int = Field(ge=0, description='Number of occurrences within the summary window')
    last_event_at: datetime | None = Field(
        default=None, description='Timestamp of the most recent occurrence in UTC'
    )


class PlanQuota(BaseModel):
    event_type: str
    limit: int | None = Field(default=None, ge=0)
    used: int = Field(default=0, ge=0)
    remaining: int | None = Field(default=None)
    window_days: int = Field(default=30, ge=1)
    status: str = Field(default='ok', description='ok | warning | limit')


class PlanAlert(BaseModel):
    event_type: str
    status: str
    message: str


class PlanSnapshot(BaseModel):
    plan_name: str
    quotas: list[PlanQuota] = Field(default_factory=list)
    alerts: list[PlanAlert] = Field(default_factory=list)
