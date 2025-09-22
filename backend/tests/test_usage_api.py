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
    asyncio.run(usage_service.log_event('properties.export', payload={'export_count': 5}, account_id='acct-1'))
    asyncio.run(usage_service.log_event('properties.lead_pack', payload={'pack_size': 25}, account_id='acct-1'))

    app.dependency_overrides[get_usage_service] = lambda: usage_service
    try:
        with TestClient(app) as client:
            response = client.get(
                '/api/usage/summary',
                params={'days': 30},
                headers={'X-Account-Id': 'acct-1'},
            )
        assert response.status_code == 200
        payload = response.json()
        event_types = {item['event_type'] for item in payload}
        assert {'properties.export', 'properties.lead_pack'} <= event_types
    finally:
        app.dependency_overrides.clear()


def test_usage_plan_endpoint(usage_service):
    app.dependency_overrides[get_usage_service] = lambda: usage_service
    try:
        asyncio.run(usage_service.log_event('properties.export', account_id='acct-1'))
        with TestClient(app) as client:
            response = client.get('/api/usage/plan', headers={'X-Account-Id': 'acct-1'})
        assert response.status_code == 200
        payload = response.json()
        assert payload['plan_name'] == 'growth'
        assert payload['plan_display_name']
        export_quota = next(quota for quota in payload['quotas'] if quota['event_type'] == 'properties.export')
        assert export_quota['used'] == 1
        assert export_quota['remaining'] == 4
        if payload['alerts']:
            assert payload['alerts'][0]['event_type'] == 'properties.export'
    finally:
        app.dependency_overrides.clear()

def test_plan_selection_and_catalog(usage_service):
    app.dependency_overrides[get_usage_service] = lambda: usage_service
    try:
        with TestClient(app) as client:
            catalog = client.get('/api/usage/catalog')
            assert catalog.status_code == 200
            names = {item['name'] for item in catalog.json()}
            assert {'starter', 'growth', 'scale'} <= names

            response = client.post(
                '/api/usage/plan/select',
                json={'plan_name': 'scale'},
                headers={'X-Account-Id': 'acct-2'},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload['plan_name'] == 'scale'

            history = client.get(
                '/api/usage/history',
                params={'days': 7},
                headers={'X-Account-Id': 'acct-2'},
            )
            assert history.status_code == 200
    finally:
        app.dependency_overrides.clear()

def test_plan_selection_requires_account_header(usage_service):
    app.dependency_overrides[get_usage_service] = lambda: usage_service
    try:
        with TestClient(app) as client:
            response = client.post('/api/usage/plan/select', json={'plan_name': 'starter'})
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()
