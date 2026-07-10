from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.exceptions import APIError, api_error_handler
from backend.routers import auth, config, data, health, inventory, system, transactions
from backend.services.db import init_db_runtime

# Honsen WMS — local API shell (desktop + dev)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db_runtime()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_exception_handler(APIError, api_error_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(inventory.router)
    app.include_router(config.router)
    app.include_router(transactions.router)
    app.include_router(data.router)
    app.include_router(system.router)

    if settings.serve_frontend and settings.static_dir:
        app.mount(
            "/",
            StaticFiles(directory=settings.static_dir, html=True),
            name="frontend",
        )

    return app


app = create_app()
