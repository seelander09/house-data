import asyncio

import pytest

from app.config import Settings
from app.models.property import PropertyFilters
from app.services.properties import PropertyService

SAMPLE_PROPERTIES = [
    {
        '_id': 'prop-1',
        'address': '123 Equity Lane',
        'city': 'Austin',
        'state': 'TX',
        'zipCode': '73301',
        'latitude': 30.2715,
        'longitude': -97.7426,
        'totalAssessedValue': 250000,
        'modelValue': 475000,
        'equityCurrentEstBal': 300000,
        'transferDate': '20240115',
        'ownerName': 'High Equity Owner',
        'ownerAddressLine1': '123 Equity Lane',
        'ownerCity': 'Austin',
        'ownerState': 'TX',
        'ownerZipCode': '73301',
        'ownerPhone': '555-123-4567',
        'ownerEmail': 'owner@equity.com',
    },
    {
        '_id': 'prop-2',
        'address': '456 Market Street',
        'city': 'Dallas',
        'state': 'TX',
        'zipCode': '75201',
        'latitude': 32.7767,
        'longitude': -96.7970,
        'totalAssessedValue': 320000,
        'modelValue': 360000,
        'equityCurrentEstBal': 120000,
        'transferDate': '20190101',
        'ownerName': 'Mid Equity Owner',
        'ownerAddressLine1': '456 Market Street',
        'ownerCity': 'Dallas',
        'ownerState': 'TX',
        'ownerZipCode': '75201',
    },
    {
        '_id': 'prop-3',
        'address': '789 Legacy Drive',
        'city': 'Austin',
        'state': 'TX',
        'zipCode': '73301',
        'latitude': 30.3200,
        'longitude': -97.7500,
        'totalAssessedValue': 500000,
        'modelValue': 510000,
        'equityCurrentEstBal': 50000,
        'transferDate': '20100101',
        'ownerName': 'Low Equity Owner',
        'ownerAddressLine1': '789 Legacy Drive',
        'ownerCity': 'Austin',
        'ownerState': 'TX',
        'ownerZipCode': '73301',
    },
    {
        '_id': 'prop-4',
        'address': '321 Absentee Ave',
        'city': 'Austin',
        'state': 'TX',
        'zipCode': '78701',
        'latitude': 30.2500,
        'longitude': -97.7500,
        'totalAssessedValue': 275000,
        'modelValue': 420000,
        'equityCurrentEstBal': 200000,
        'transferDate': '20230202',
        'ownerName': 'Investor Owner',
        'ownerAddressLine1': '900 Remote Road',
        'ownerCity': 'Houston',
        'ownerState': 'TX',
        'ownerZipCode': '77002',
    },
]


class DummyRealieClient:
    async def fetch_all_properties(self, max_records=None, page_size=100):  # noqa: D401
        return SAMPLE_PROPERTIES


@pytest.fixture
def service():
    settings = Settings(
        REALIE_API_KEY='test-key',
        CACHE_TTL_SECONDS=0,
        MAX_PROPERTIES=100,
        ENABLE_SCHEDULER=False,
    )
    return PropertyService(client=DummyRealieClient(), settings=settings)


@pytest.mark.asyncio
async def test_properties_are_scored_and_sorted(service: PropertyService):
    response = await service.list_properties(PropertyFilters(limit=10, offset=0))

    assert response.total == len(SAMPLE_PROPERTIES)
    scores = [item.listing_score for item in response.items]
    assert scores == sorted(scores, reverse=True)
    assert response.items[0].owner.name == 'High Equity Owner'
    assert response.items[0].owner_occupancy == 'owner_occupied'
    assert response.items[0].value_gap is not None


@pytest.mark.asyncio
async def test_filters_by_minimum_equity(service: PropertyService):
    response = await service.list_properties(PropertyFilters(limit=10, offset=0, min_equity=200000))

    ids = [item.property_id for item in response.items]
    assert ids == ['prop-1', 'prop-4']


@pytest.mark.asyncio
async def test_filters_by_owner_occupancy(service: PropertyService):
    absentee = await service.list_properties(PropertyFilters(limit=10, offset=0, owner_occupancy='absentee'))
    assert absentee.total == 1
    assert absentee.items[0].property_id == 'prop-4'

    owner_occ = await service.list_properties(PropertyFilters(limit=10, offset=0, owner_occupancy='owner'))
    assert owner_occ.total == 3


@pytest.mark.asyncio
async def test_radius_filter(service: PropertyService):
    filters = PropertyFilters(
        limit=10,
        offset=0,
        center_latitude=30.2711,
        center_longitude=-97.7437,
        radius_miles=5,
    )
    response = await service.list_properties(filters)

    assert all(item.distance_from_search_center_miles is not None for item in response.items)
    assert response.total >= 2  # Austin properties only


@pytest.mark.asyncio
async def test_spawn_and_shutdown_refresh_task(service: PropertyService):
    service._scheduler_enabled = True  # enable for test
    task = service.spawn_refresh_task()
    assert task is not None
    await service.shutdown_refresh_task()
    assert service._refresh_task is None
