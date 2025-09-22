import io

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_property_service, get_usage_service
from app.main import app
from app.services.properties import PropertyService
from app.services.usage import UsageLimitError
from tests.test_properties_service import DummyRealieClient, SAMPLE_PROPERTIES


def _build_service() -> PropertyService:
    settings = Settings(
        REALIE_API_KEY='test-key',
        CACHE_TTL_SECONDS=0,
        MAX_PROPERTIES=100,
        ENABLE_SCHEDULER=False,
    )
    return PropertyService(client=DummyRealieClient(), settings=settings)


class _NoopUsageService:
    async def log_event(self, *args, **kwargs) -> None:  # noqa: D401
        return None

    async def get_summary(self, *args, **kwargs) -> list:  # noqa: D401
        return []

    @property
    def enabled(self) -> bool:  # noqa: D401
        return False

    async def ensure_within_plan(self, *args, **kwargs) -> None:  # noqa: D401
        return None

    async def get_plan_snapshot(self, *args, **kwargs):  # noqa: D401
        return None

    async def get_usage_history(self, *args, **kwargs):  # noqa: D401
        return []

    async def get_recent_alerts(self, *args, **kwargs):  # noqa: D401
        return []

    async def get_plan_catalog(self, *args, **kwargs):  # noqa: D401
        return []

    async def set_plan_for_account(self, *args, **kwargs):  # noqa: D401
        return None


class _LimitedUsageService(_NoopUsageService):
    async def ensure_within_plan(self, *args, **kwargs) -> None:  # noqa: D401
        raise UsageLimitError('Plan usage limit reached')


@pytest.fixture
def client():
    service = _build_service()
    usage_service = _NoopUsageService()
    app.dependency_overrides[get_property_service] = lambda: service
    app.dependency_overrides[get_usage_service] = lambda: usage_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_properties_endpoint(client: TestClient):
    response = client.get('/api/properties', params={'limit': 5})
    assert response.status_code == 200

    payload = response.json()
    assert payload['total'] == len(SAMPLE_PROPERTIES)
    first = payload['items'][0]
    assert 'owner_occupancy' in first
    assert 'value_gap' in first


def test_export_properties_headers(client: TestClient):
    response = client.get('/api/properties/export', params={'owner_occupancy': 'absentee'})
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/csv')
    assert response.headers['x-property-count'] == '1'

    content = response.content.decode('utf-8')
    assert 'owner_occupancy' in content


def test_radius_validation_error(client: TestClient):
    response = client.get('/api/properties', params={'radius_miles': 5})
    assert response.status_code == 422
    assert 'center_latitude' in response.json()['detail']

def test_lead_packs_endpoint(client: TestClient):
    response = client.get('/api/properties/packs', params={'group_by': 'city', 'pack_size': 2})
    assert response.status_code == 200
    payload = response.json()
    assert 'packs' in payload
    assert payload['packs']
    first_pack = payload['packs'][0]
    assert 'top_properties' in first_pack
    assert first_pack['top_properties']


def test_export_respects_plan_limit():
    service = _build_service()
    usage = _LimitedUsageService()
    app.dependency_overrides[get_property_service] = lambda: service
    app.dependency_overrides[get_usage_service] = lambda: usage

    try:
        with TestClient(app) as test_client:
            response = test_client.get('/api/properties/export')
        assert response.status_code == 429
        assert 'Plan usage limit reached' in response.json()['detail']
    finally:
        app.dependency_overrides.clear()

