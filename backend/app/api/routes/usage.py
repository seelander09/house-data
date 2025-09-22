from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status

from ...dependencies import get_usage_service
from ...models.usage import (
    PlanDefinition,
    PlanSelectionRequest,
    PlanSnapshot,
    UsageAlertRecord,
    UsageHistoryEntry,
    UsageSummary,
)
from ...services.usage import UsageService


router = APIRouter(prefix='/usage', tags=['usage'])


def _usage_context(request: Request) -> tuple[str | None, str | None]:
    account_id = request.headers.get('x-account-id') or request.headers.get('X-Account-Id')
    user_id = request.headers.get('x-user-id') or request.headers.get('X-User-Id')
    return account_id, user_id


@router.get('/summary', response_model=list[UsageSummary])
async def usage_summary(
    request: Request,
    days: Annotated[int, Query(ge=1, le=365, description='Number of days to include in the summary')] = 30,
    usage_service: UsageService = Depends(get_usage_service),
) -> list[UsageSummary]:
    account_id, _ = _usage_context(request)
    return await usage_service.get_summary(days=days, account_id=account_id)


@router.get('/plan', response_model=PlanSnapshot)
async def plan_snapshot(
    request: Request,
    usage_service: UsageService = Depends(get_usage_service),
) -> PlanSnapshot:
    account_id, _ = _usage_context(request)
    return await usage_service.get_plan_snapshot(account_id=account_id)


@router.get('/history', response_model=list[UsageHistoryEntry])
async def usage_history(
    request: Request,
    days: Annotated[int, Query(ge=1, le=365, description='Rolling window length')] = 30,
    usage_service: UsageService = Depends(get_usage_service),
) -> list[UsageHistoryEntry]:
    account_id, _ = _usage_context(request)
    return await usage_service.get_usage_history(days=days, account_id=account_id)


@router.get('/alerts', response_model=list[UsageAlertRecord])
async def recent_alerts(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100, description='Maximum alerts to return')] = 20,
    usage_service: UsageService = Depends(get_usage_service),
) -> list[UsageAlertRecord]:
    account_id, _ = _usage_context(request)
    return await usage_service.get_recent_alerts(account_id=account_id, limit=limit)


@router.get('/catalog', response_model=list[PlanDefinition])
async def plan_catalog(usage_service: UsageService = Depends(get_usage_service)) -> list[PlanDefinition]:
    return await usage_service.get_plan_catalog()


@router.post('/plan/select', response_model=PlanSnapshot, status_code=status.HTTP_200_OK)
async def select_plan(
    request: Request,
    payload: PlanSelectionRequest = Body(..., description='Requested plan selection'),
    usage_service: UsageService = Depends(get_usage_service),
) -> PlanSnapshot:
    account_id, _ = _usage_context(request)
    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='X-Account-Id header is required to change plans',
        )
    try:
        return await usage_service.set_plan_for_account(account_id, payload.plan_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
