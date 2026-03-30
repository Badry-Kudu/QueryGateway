"""DB2API-Exposure FastAPI application factory.

Responsibilities of this module:
- Create the FastAPI instance with metadata and lifespan.
- Register middleware (ordering matters: outermost first).
- Register global exception handlers.
- Mount all versioned routers.

Keep business logic out of this file.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.exceptions import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.logging_config import configure_logging
from app.middleware import RequestLoggingMiddleware
from app.routers import (
    auth_methods,
    connections,
    data,
    endpoints,
    health,
    schedules,
)
from app.routers import (
    settings as settings_router,
)
from app.services.scheduler import start_scheduler, stop_scheduler

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    configure_logging(settings.log_level)
    log.info(
        "application_startup",
        env=settings.app_env,
        debug=settings.debug,
    )
    start_scheduler()
    yield
    stop_scheduler()
    log.info("application_shutdown")


app = FastAPI(
    title="DB2API-Exposure",
    description="Secure, dynamic REST endpoints from Oracle SQL queries.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware (registered outermost-first; executes in reverse order) ────────

# CORSMiddleware must be registered before RequestLoggingMiddleware so CORS
# headers are applied to error responses as well.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

# ── Exception handlers ────────────────────────────────────────────────────────

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(connections.router)
app.include_router(auth_methods.router)
app.include_router(endpoints.router)
app.include_router(schedules.router)
app.include_router(settings_router.router)
app.include_router(data.router)
