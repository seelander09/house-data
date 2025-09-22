import asyncio

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_usage_service
from app.main import app
from app.services.usage import UsageService


@pytest.fixture
def usage_service(tmp_path):
    settings = Settings(
        REALIE_API_KEY='test-key',
        ENABLE_USAGE_TRACKING=True,
        USAGE_DB_PATH=str(tmp_path / 'usage-api.db'),
        PLAN_EXPORT_LIMIT=5,
        PLAN_LEAD_PACK_LIMIT=3,
        PLAN_REFRESH_LIMIT=2,
    )
    return UsageService(settings)


def test_usage_summary_endpoint(tmp_path, usage_service):
    asyncio.run(usage_service.log_event('properties.export', payload={'export_count': 5}))
    asyncio.run(usage_service.log_event('properties.lead_pack', payload={'pack_size': 25}))

    app.dependency_overrides[get_usage_service] = lambda: usage_service
    try:
        with TestClient(app) as client:
            response = client.get('/api/usage/summary', params={'days': 30})
        assert response.status_code == 200
        payload = response.json()
        event_types = {item['event_type'] for item in payload}
        assert {'properties.export', 'properties.lead_pack'} <= event_types
    finally:
        app.dependency_overrides.clear()


def test_usage_plan_endpoint(usage_service):
    app.dependency_overrides[get_usage_service] = lambda: usage_service
    try:
        asyncio.run(usage_service.log_event('properties.export'))
        with TestClient(app) as client:
            response = client.get('/api/usage/plan')
        assert response.status_code == 200
        payload = response.json()
        assert payload['plan_name'] == usage_service._plan_name  # noqa: SLF001
        export_quota = next(quota for quota in payload['quotas'] if quota['event_type'] == 'properties.export')
        assert export_quota['used'] == 1
        assert export_quota['remaining'] == 4
        if payload['alerts']:
            assert payload['alerts'][0]['event_type'] == 'properties.export'
    finally:
        app.dependency_overrides.clear()
