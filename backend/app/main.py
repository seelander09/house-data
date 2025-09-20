from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import properties
from .config import get_settings
from .dependencies import get_property_service

settings = get_settings()

app = FastAPI(title='Realtor Lead Radar API', version='0.2.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
async def startup_event() -> None:
    service = get_property_service()
    task = service.spawn_refresh_task()
    if task:
        app.state.refresh_task = task


@app.on_event('shutdown')
async def shutdown_event() -> None:
    service = get_property_service()
    await service.shutdown_refresh_task()


@app.get('/health', tags=['health'])
async def health_check() -> dict[str, str]:
    return {'status': 'ok'}


app.include_router(properties.router, prefix='/api')
