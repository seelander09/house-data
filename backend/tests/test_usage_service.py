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

    await service.log_event('properties.export', payload={'export_count': 3}, account_id='acct-1')
    await service.log_event('properties.export', payload={'export_count': 1}, account_id='acct-1')
    await service.log_event('properties.lead_pack', payload={'pack_size': 50}, account_id='acct-1')

    summary = await service.get_summary(days=7, account_id='acct-1')
    summary_map = {item.event_type: item for item in summary}

    assert summary_map['properties.export'].count == 2
    assert summary_map['properties.lead_pack'].count == 1
    assert isinstance(summary_map['properties.export'].last_event_at, datetime)

    history = await service.get_usage_history(days=7, account_id='acct-1')
    assert any(row.event_type == 'properties.export' for row in history)


@pytest.mark.asyncio
async def test_usage_service_can_be_disabled(tmp_path):
    settings = Settings(
        REALIE_API_KEY='test-key',
        ENABLE_USAGE_TRACKING=False,
        USAGE_DB_PATH=str(tmp_path / 'unused.db'),
    )

    service = UsageService(settings)
    await service.log_event('properties.export', account_id='acct-1')
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
    await service.ensure_within_plan('properties.export', account_id='acct-1')
    await service.log_event('properties.export', account_id='acct-1')

    # Next export should exceed the plan
    with pytest.raises(UsageLimitError):
        await service.ensure_within_plan('properties.export', account_id='acct-1')

    snapshot = await service.get_plan_snapshot(account_id='acct-1')
    quota_map = {quota.event_type: quota for quota in snapshot.quotas}
    assert quota_map['properties.export'].used == 1
    assert quota_map['properties.export'].remaining == 0
    assert snapshot.alerts
    first_alert = snapshot.alerts[0]
    assert first_alert.status == 'limit'
    assert 'properties.export' in first_alert.message
    alerts = await service.get_recent_alerts(account_id='acct-1', limit=5)
    assert alerts


    assert snapshot.plan_display_name


@pytest.mark.asyncio
async def test_plan_catalog_and_selection(tmp_path):
    settings = Settings(
        REALIE_API_KEY='test-key',
        ENABLE_USAGE_TRACKING=True,
        USAGE_DB_PATH=str(tmp_path / 'catalog.db'),
    )

    service = UsageService(settings)
    catalog = await service.get_plan_catalog()
    plan_names = {plan.name for plan in catalog}
    assert {'starter', 'growth', 'scale'} <= plan_names

    snapshot = await service.set_plan_for_account('acct-2', 'scale')
    assert snapshot.plan_name == 'scale'
    assert snapshot.plan_display_name.lower() == 'scale'
    assert snapshot.plan_display_name.lower() == 'scale'
