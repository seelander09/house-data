from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment."""

    realie_api_key: str = Field(alias='REALIE_API_KEY')
    realie_base_url: str = Field(
        default='https://app.realie.ai/api/public/property/search/',
        alias='REALIE_BASE_URL',
    )
    cache_ttl_seconds: int = Field(default=300, alias='CACHE_TTL_SECONDS')
    request_timeout: float = Field(default=10.0, alias='REQUEST_TIMEOUT')
    max_properties: int = Field(default=500, alias='MAX_PROPERTIES')
    cors_allow_origins: List[str] = Field(
        default_factory=lambda: ['http://localhost:5173', 'http://127.0.0.1:5173'],
        alias='CORS_ALLOW_ORIGINS',
    )

    cache_backend: str = Field(default='memory', alias='CACHE_BACKEND')
    redis_url: str | None = Field(default=None, alias='REDIS_URL')
    cache_namespace: str = Field(default='lead-radar', alias='CACHE_NAMESPACE')
    refresh_interval_seconds: int = Field(default=900, alias='REFRESH_INTERVAL_SECONDS')
    enable_scheduler: bool = Field(default=True, alias='ENABLE_SCHEDULER')
    scoring_equity_weight: float = Field(default=0.45, alias='SCORING_EQUITY_WEIGHT')
    scoring_value_gap_weight: float = Field(default=0.35, alias='SCORING_VALUE_GAP_WEIGHT')
    scoring_recency_weight: float = Field(default=0.20, alias='SCORING_RECENCY_WEIGHT')

    model_config = SettingsConfigDict(
        env_file=('.env',), env_file_encoding='utf-8', extra='ignore', env_parse_delimiter=','
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
