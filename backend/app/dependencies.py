from functools import lru_cache

from .config import Settings, get_settings
from .clients.realie import RealieClient
from .services.properties import PropertyService


@lru_cache
def get_realie_client() -> RealieClient:
    settings = get_settings()
    return RealieClient(settings=settings)


@lru_cache
def get_property_service() -> PropertyService:
    return PropertyService(client=get_realie_client(), settings=get_settings())
