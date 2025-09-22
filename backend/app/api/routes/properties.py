from __future__ import annotations

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.responses import StreamingResponse

from ...dependencies import get_property_service, get_usage_service
from ...models.property import LeadPackResponse, PropertyFilters, PropertyListResponse
from ...services.properties import PropertyService
from ...services.usage import UsageLimitError, UsageService

router = APIRouter(prefix='/properties', tags=['properties'])


def _usage_context(request: Request) -> tuple[str | None, str | None]:
    account_id = request.headers.get('x-account-id') or request.headers.get('X-Account-Id')
    user_id = request.headers.get('x-user-id') or request.headers.get('X-User-Id')
    return account_id, user_id


@router.get('/', response_model=PropertyListResponse)
async def list_properties(
    request: Request,
    city: Annotated[str | None, Query(description='City filter (contains match)', min_length=2)] = None,
    state: Annotated[str | None, Query(description='State/region filter', min_length=2)] = None,
    postal_code: Annotated[str | None, Query(description='Postal/zip prefix filter', min_length=3, max_length=10)] = None,
    min_equity: Annotated[float | None, Query(description='Minimum equity in USD')] = None,
    min_score: Annotated[float | None, Query(description='Minimum listing score (0-100)')] = None,
    min_value_gap: Annotated[float | None, Query(description='Minimum value gap in USD')] = None,
    min_market_value: Annotated[float | None, Query(description='Minimum market value in USD')] = None,
    max_market_value: Annotated[float | None, Query(description='Maximum market value in USD')] = None,
    min_assessed_value: Annotated[float | None, Query(description='Minimum assessed value in USD')] = None,
    max_assessed_value: Annotated[float | None, Query(description='Maximum assessed value in USD')] = None,
    owner_occupancy: Annotated[str | None, Query(description='owner_occupied or absentee')] = None,
    center_latitude: Annotated[float | None, Query(description='Latitude for radius filter')] = None,
    center_longitude: Annotated[float | None, Query(description='Longitude for radius filter')] = None,
    radius_miles: Annotated[float | None, Query(gt=0, description='Radius in miles for spatial search')] = None,
    search: Annotated[str | None, Query(description='Free text search across address, owner and IDs')] = None,
    limit: Annotated[int, Query(ge=1, le=200, description='Maximum records to return')] = 50,
    offset: Annotated[int, Query(ge=0, description='Pagination offset')] = 0,
    service: PropertyService = Depends(get_property_service),
    usage_service: UsageService = Depends(get_usage_service),
) -> PropertyListResponse:
    filters = PropertyFilters(
        city=city,
        state=state,
        postal_code=postal_code,
        min_equity=min_equity,
        min_score=min_score,
        min_value_gap=min_value_gap,
        min_market_value=min_market_value,
        max_market_value=max_market_value,
        min_assessed_value=min_assessed_value,
        max_assessed_value=max_assessed_value,
        owner_occupancy=owner_occupancy,
        center_latitude=center_latitude,
        center_longitude=center_longitude,
        radius_miles=radius_miles,
        search=search,
        limit=limit,
        offset=offset,
    )
    try:
        filters.normalize_for_radius()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id, user_id = _usage_context(request)
    response = await service.list_properties(filters)
    await usage_service.log_event(
        'properties.list',
        payload={
            'limit': filters.limit,
            'offset': filters.offset,
            'returned': len(response.items),
            'filters': filters.model_dump(exclude_none=True),
        },
        metadata={'total_available': response.total},
        account_id=account_id,
        user_id=user_id,
    )
    return response


@router.get('/packs', response_model=LeadPackResponse)
async def get_lead_packs(
    request: Request,
    city: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    postal_code: Annotated[str | None, Query()] = None,
    min_equity: Annotated[float | None, Query()] = None,
    min_score: Annotated[float | None, Query()] = None,
    min_value_gap: Annotated[float | None, Query()] = None,
    min_market_value: Annotated[float | None, Query()] = None,
    max_market_value: Annotated[float | None, Query()] = None,
    min_assessed_value: Annotated[float | None, Query()] = None,
    max_assessed_value: Annotated[float | None, Query()] = None,
    owner_occupancy: Annotated[str | None, Query()] = None,
    center_latitude: Annotated[float | None, Query()] = None,
    center_longitude: Annotated[float | None, Query()] = None,
    radius_miles: Annotated[float | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    group_by: Annotated[str, Query(description='Grouping dimension: postal_code, city, or state')] = 'postal_code',
    pack_size: Annotated[int, Query(ge=1, le=500, description='Max listings per pack')] = 200,
    service: PropertyService = Depends(get_property_service),
    usage_service: UsageService = Depends(get_usage_service),
) -> LeadPackResponse:
    filters = PropertyFilters(
        city=city,
        state=state,
        postal_code=postal_code,
        min_equity=min_equity,
        min_score=min_score,
        min_value_gap=min_value_gap,
        min_market_value=min_market_value,
        max_market_value=max_market_value,
        min_assessed_value=min_assessed_value,
        max_assessed_value=max_assessed_value,
        owner_occupancy=owner_occupancy,
        center_latitude=center_latitude,
        center_longitude=center_longitude,
        radius_miles=radius_miles,
        search=search,
        limit=service.max_properties,
        offset=0,
    )
    try:
        filters.normalize_for_radius()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    account_id, user_id = _usage_context(request)
    try:
        await usage_service.ensure_within_plan('properties.lead_pack', account_id=account_id)
    except UsageLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    response = await service.generate_lead_packs(filters, group_by=group_by, pack_size=pack_size)
    await usage_service.log_event(
        'properties.lead_pack',
        payload={
            'group_by': group_by,
            'pack_size': pack_size,
            'filters': filters.model_dump(exclude_none=True),
            'pack_count': len(response.packs),
        },
        account_id=account_id,
        user_id=user_id,
    )
    return response


@router.get('/export')
async def export_properties(
    request: Request,
    city: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    postal_code: Annotated[str | None, Query()] = None,
    min_equity: Annotated[float | None, Query()] = None,
    min_score: Annotated[float | None, Query()] = None,
    min_value_gap: Annotated[float | None, Query()] = None,
    min_market_value: Annotated[float | None, Query()] = None,
    max_market_value: Annotated[float | None, Query()] = None,
    min_assessed_value: Annotated[float | None, Query()] = None,
    max_assessed_value: Annotated[float | None, Query()] = None,
    owner_occupancy: Annotated[str | None, Query()] = None,
    center_latitude: Annotated[float | None, Query()] = None,
    center_longitude: Annotated[float | None, Query()] = None,
    radius_miles: Annotated[float | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    service: PropertyService = Depends(get_property_service),
    usage_service: UsageService = Depends(get_usage_service),
) -> StreamingResponse:
    filters = PropertyFilters(
        city=city,
        state=state,
        postal_code=postal_code,
        min_equity=min_equity,
        min_score=min_score,
        min_value_gap=min_value_gap,
        min_market_value=min_market_value,
        max_market_value=max_market_value,
        min_assessed_value=min_assessed_value,
        max_assessed_value=max_assessed_value,
        owner_occupancy=owner_occupancy,
        center_latitude=center_latitude,
        center_longitude=center_longitude,
        radius_miles=radius_miles,
        search=search,
        limit=500,
        offset=0,
    )
    try:
        filters.normalize_for_radius()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    account_id, user_id = _usage_context(request)
    try:
        await usage_service.ensure_within_plan('properties.export', account_id=account_id)
    except UsageLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    properties = await service.export_properties(filters)
    await usage_service.log_event(
        'properties.export',
        payload={
            'filters': filters.model_dump(exclude_none=True),
            'export_count': len(properties),
        },
        account_id=account_id,
        user_id=user_id,
    )

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
        'owner_phone',
        'owner_email',
        'total_assessed_value',
        'total_market_value',
        'equity_available',
        'value_gap',
        'owner_occupancy',
        'listing_score',
        'distance_from_search_center_miles',
    ]

    def iter_rows():
        buffer = io.StringIO()
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
                    'owner_phone': item.owner.phone,
                    'owner_email': item.owner.email,
                    'total_assessed_value': item.total_assessed_value,
                    'total_market_value': item.total_market_value or item.model_value,
                    'equity_available': item.equity_available,
                    'value_gap': item.value_gap,
                    'owner_occupancy': item.owner_occupancy,
                    'listing_score': item.listing_score,
                    'distance_from_search_center_miles': item.distance_from_search_center_miles,
                }
            )
        buffer.seek(0)
        yield from buffer.getvalue().splitlines(keepends=True)

    filename = 'lead-radar-export.csv'
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'X-Property-Count': str(len(properties)),
    }
    return StreamingResponse(iter_rows(), media_type='text/csv', headers=headers)


@router.post('/refresh-cache', status_code=202)
async def refresh_cache(
    request: Request,
    service: PropertyService = Depends(get_property_service),
    usage_service: UsageService = Depends(get_usage_service),
) -> dict[str, str]:
    account_id, user_id = _usage_context(request)
    try:
        await usage_service.ensure_within_plan('properties.refresh_cache', account_id=account_id)
    except UsageLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    await service.refresh_cache(force=True)
    await usage_service.log_event('properties.refresh_cache', account_id=account_id, user_id=user_id)
    return {'status': 'cache refreshed'}
