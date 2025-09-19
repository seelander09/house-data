from __future__ import annotations

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette.responses import StreamingResponse

from ...dependencies import get_property_service
from ...models.property import PropertyFilters, PropertyListResponse
from ...services.properties import PropertyService

router = APIRouter(prefix='/properties', tags=['properties'])


@router.get('/', response_model=PropertyListResponse)
async def list_properties(
    city: Annotated[str | None, Query(description='Exact city filter', min_length=2)] = None,
    state: Annotated[str | None, Query(description='Two-letter state filter', min_length=2, max_length=2)] = None,
    min_equity: Annotated[float | None, Query(description='Minimum equity in USD')] = None,
    min_score: Annotated[float | None, Query(description='Minimum listing score (0-100)')] = None,
    search: Annotated[str | None, Query(description='Free text search across address and owner name')] = None,
    limit: Annotated[int, Query(ge=1, le=200, description='Maximum records to return')] = 50,
    offset: Annotated[int, Query(ge=0, description='Pagination offset')] = 0,
    service: PropertyService = Depends(get_property_service),
) -> PropertyListResponse:
    filters = PropertyFilters(
        city=city,
        state=state,
        min_equity=min_equity,
        min_score=min_score,
        search=search,
        limit=limit,
        offset=offset,
    )
    return await service.list_properties(filters)


@router.get('/export')
async def export_properties(
    city: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    min_equity: Annotated[float | None, Query()] = None,
    min_score: Annotated[float | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    service: PropertyService = Depends(get_property_service),
) -> StreamingResponse:
    filters = PropertyFilters(
        city=city,
        state=state,
        min_equity=min_equity,
        min_score=min_score,
        search=search,
        limit=200,
        offset=0,
    )
    properties = await service.export_properties(filters)

    def iter_rows():
        buffer = io.StringIO()
        fieldnames = [
            'property_id',
            'address',
            'city',
            'state',
            'postal_code',
            'owner_name',
            'owner_address',
            'owner_city',
            'owner_state',
            'owner_postal_code',
            'total_assessed_value',
            'total_market_value',
            'equity_available',
            'listing_score',
        ]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for item in properties:
            writer.writerow(
                {
                    'property_id': item.property_id,
                    'address': item.address,
                    'city': item.city,
                    'state': item.state,
                    'postal_code': item.postal_code,
                    'owner_name': item.owner.name,
                    'owner_address': item.owner.address_line1,
                    'owner_city': item.owner.city,
                    'owner_state': item.owner.state,
                    'owner_postal_code': item.owner.postal_code,
                    'total_assessed_value': item.total_assessed_value,
                    'total_market_value': item.total_market_value,
                    'equity_available': item.equity_available,
                    'listing_score': item.listing_score,
                }
            )
        buffer.seek(0)
        yield from buffer.getvalue().splitlines(keepends=True)

    filename = 'lead-radar-export.csv'
    return StreamingResponse(
        iter_rows(),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.post('/refresh-cache', status_code=202)
async def refresh_cache(service: PropertyService = Depends(get_property_service)) -> dict[str, str]:
    await service.refresh_cache(force=True)
    return {'status': 'cache refreshed'}
