from datetime import datetime

import pytest

from app.config import Settings
from app.services.usage import UsageLimitError, UsageService


@pytest.mark.asyncio
async def test_usage_events_are_logged_and_summarised(tmp_path):
    db_path = tmp_path / 'usage.db'
    settings = Settings(
        REALIE_API_KEY='test-key',
        ENABLE_USAGE_TRACKING=True,
        USAGE_DB_PATH=str(db_path),
        PLAN_EXPORT_LIMIT=10,
        PLAN_LEAD_PACK_LIMIT=5,
        PLAN_REFRESH_LIMIT=2,
    )

    service = UsageService(settings)

    await service.log_event('properties.export', payload={'export_count': 3})
    await service.log_event('properties.export', payload={'export_count': 1})
    await service.log_event('properties.lead_pack', payload={'pack_size': 50})

    summary = await service.get_summary(days=7)
    summary_map = {item.event_type: item for item in summary}

    assert summary_map['properties.export'].count == 2
    assert summary_map['properties.lead_pack'].count == 1
    assert isinstance(summary_map['properties.export'].last_event_at, datetime)


@pytest.mark.asyncio
async def test_usage_service_can_be_disabled(tmp_path):
    settings = Settings(
        REALIE_API_KEY='test-key',
        ENABLE_USAGE_TRACKING=False,
        USAGE_DB_PATH=str(tmp_path / 'unused.db'),
    )

    service = UsageService(settings)
    await service.log_event('properties.export')
    assert await service.get_summary() == []


@pytest.mark.asyncio
async def test_plan_limits_are_enforced(tmp_path):
    settings = Settings(
        REALIE_API_KEY='test-key',
        ENABLE_USAGE_TRACKING=True,
        USAGE_DB_PATH=str(tmp_path / 'plan.db'),
        PLAN_EXPORT_LIMIT=1,
        PLAN_LEAD_PACK_LIMIT=1,
        PLAN_REFRESH_LIMIT=0,
        PLAN_WINDOW_DAYS=30,
    )

    service = UsageService(settings)

    # First export is allowed
    await service.ensure_within_plan('properties.export')
    await service.log_event('properties.export')

    # Next export should exceed the plan
    with pytest.raises(UsageLimitError):
        await service.ensure_within_plan('properties.export')

    snapshot = await service.get_plan_snapshot()
    quota_map = {quota.event_type: quota for quota in snapshot.quotas}
    assert quota_map['properties.export'].used == 1
    assert quota_map['properties.export'].remaining == 0
    assert snapshot.alerts
    first_alert = snapshot.alerts[0]
    assert first_alert.status == 'limit'
    assert 'properties.export' in first_alert.message
