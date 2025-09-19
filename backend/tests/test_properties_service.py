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
        'totalAssessedValue': 250000,
        'modelValue': 475000,
        'equityCurrentEstBal': 300000,
        'transferDate': '20240115',
        'ownerName': 'High Equity Owner',
        'ownerAddressLine1': '123 Equity Lane',
        'ownerCity': 'Austin',
        'ownerState': 'TX',
        'ownerZipCode': '73301',
    },
    {
        '_id': 'prop-2',
        'address': '456 Market Street',
        'city': 'Dallas',
        'state': 'TX',
        'zipCode': '75201',
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
]


class DummyRealieClient:
    async def fetch_all_properties(self, max_records=None, page_size=100):  # noqa: D401
        return SAMPLE_PROPERTIES


@pytest.mark.asyncio
async def test_properties_are_scored_and_sorted():
    settings = Settings(REALIE_API_KEY='test-key', CACHE_TTL_SECONDS=0, MAX_PROPERTIES=100)
    service = PropertyService(client=DummyRealieClient(), settings=settings)

    response = await service.list_properties(PropertyFilters(limit=10, offset=0))

    assert response.total == 3
    scores = [item.listing_score for item in response.items]
    assert scores == sorted(scores, reverse=True)
    assert response.items[0].owner.name == 'High Equity Owner'


@pytest.mark.asyncio
async def test_filters_by_minimum_equity():
    settings = Settings(REALIE_API_KEY='test-key', CACHE_TTL_SECONDS=0, MAX_PROPERTIES=100)
    service = PropertyService(client=DummyRealieClient(), settings=settings)

    response = await service.list_properties(PropertyFilters(limit=10, offset=0, min_equity=200000))

    assert response.total == 1
    assert response.items[0].property_id == 'prop-1'
