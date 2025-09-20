import io

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.services.properties import PropertyService
from tests.test_properties_service import DummyRealieClient, SAMPLE_PROPERTIES


def _build_service() -> PropertyService:
    settings = Settings(
        REALIE_API_KEY='test-key',
        CACHE_TTL_SECONDS=0,
        MAX_PROPERTIES=100,
        ENABLE_SCHEDULER=False,
    )
    return PropertyService(client=DummyRealieClient(), settings=settings)


@pytest.fixture
def client():
    service = _build_service()

    from app.dependencies import get_property_service

    app.dependency_overrides[get_property_service] = lambda: service
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

