from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import properties
from .config import get_settings

settings = get_settings()

app = FastAPI(title='Realtor Lead Radar API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health', tags=['health'])
async def health_check() -> dict[str, str]:
    return {'status': 'ok'}


app.include_router(properties.router, prefix='/api')
