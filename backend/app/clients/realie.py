from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from ..config import Settings


class RealieClient:
    """Thin wrapper around the Realie public property API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = settings.realie_base_url.rstrip('/') + '/'
        self._headers = {
            'Authorization': settings.realie_api_key,
            'Accept': 'application/json',
        }
        self._timeout = settings.request_timeout

    async def fetch_properties(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {'limit': limit, 'offset': offset}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(self._base_url, params=params, headers=self._headers)
        response.raise_for_status()
        payload: Dict[str, Any] = response.json()
        properties: List[Dict[str, Any]] = payload.get('properties', [])
        return properties

    async def fetch_all_properties(self, max_records: Optional[int] = None, page_size: int = 100) -> List[Dict[str, Any]]:
        """Paginate through the API until ``max_records`` is reached or no more data."""
        collected: List[Dict[str, Any]] = []
        offset = 0
        max_records = max_records or self._settings.max_properties

        while True:
            remaining = max_records - len(collected)
            if remaining <= 0:
                break

            chunk = await self.fetch_properties(limit=min(page_size, remaining), offset=offset)
            if not chunk:
                break

            collected.extend(chunk)
            offset += len(chunk)

            if len(chunk) < page_size:
                break

        return collected
