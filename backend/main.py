import asyncio
import contextlib
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import create_all
from backend.errors import register_exception_handlers
from backend.middleware import (
    BackendHardeningMiddleware,
    configure_structured_logging,
    startup_self_check,
)
from backend.routers import (
    analyze,
    chaos,
    db_inspector,
    emergency,
    endpoints,
    incidents,
    kpis,
    probe,
    remediate,
    settings as settings_router,
    stream,
)
from backend.schemas import HealthResponse


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    configure_structured_logging()
    startup_self_check()
    create_all()
    monitor_task = None
    if settings.monitor_enabled:
        from backend.services.monitor import monitor_loop

        monitor_task = asyncio.create_task(monitor_loop(), name="opspilot-monitor")
        _app.state.monitor_task = monitor_task
    try:
        yield
    finally:
        if monitor_task is not None:
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task


def create_app() -> FastAPI:
    production = settings.env.strip().lower() == "production"
    app = FastAPI(
        title="OpsPilot",
        lifespan=lifespan,
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BackendHardeningMiddleware)
    register_exception_handlers(app)

    for router in (
        probe.router,
        chaos.router,
        remediate.router,
        emergency.router,
        incidents.router,
        kpis.router,
        endpoints.router,
        settings_router.router,
        db_inspector.router,
        stream.router,
        analyze.router,
    ):
        app.include_router(router, prefix="/api")

    app.include_router(analyze.router)

    @app.get("/health")
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="OpsPilot")

    return app


app = create_app()
