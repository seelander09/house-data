from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from ...dependencies import get_usage_service
from ...models.usage import PlanSnapshot, UsageSummary
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
