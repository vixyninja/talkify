import contextlib
from collections.abc import AsyncGenerator, Callable
from typing import Any

import anyio
import fastapi
import fastapi.middleware
import fastapi.middleware.cors
import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..api.dependencies import get_current_superuser
from ..middleware.client_cache_middleware import ClientCacheMiddleware
from .config import (
    AppSettings,
    ClientSideCacheSettings,
    CORSSettings,
    DatabaseSettings,
    EnvironmentOption,
    EnvironmentSettings,
    RedisCacheSettings,
    RedisQueueSettings,
    settings,
)
from .db.database import Base
from .db.database import async_engine as engine
from .utils import cache, queue


# -------------- database --------------
async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# -------------- cache --------------
async def create_redis_cache_pool() -> None:
    cache.pool = redis.ConnectionPool.from_url(settings.REDIS_CACHE_URL)
    cache.client = redis.Redis.from_pool(cache.pool)


async def close_redis_cache_pool() -> None:
    if cache.client is not None:
        await cache.client.aclose()


# -------------- queue --------------
async def create_redis_queue_pool() -> None:
    queue.pool = await create_pool(RedisSettings(host=settings.REDIS_QUEUE_HOST, port=settings.REDIS_QUEUE_PORT))


async def close_redis_queue_pool() -> None:
    if queue.pool is not None:
        await queue.pool.aclose()


# -------------- application --------------
async def set_threadpool_tokens(number_of_tokens: int = 100) -> None:
    limiter = anyio.to_thread.current_default_thread_limiter()  # type: ignore
    limiter.total_tokens = number_of_tokens


def lifespan_factory(
    _settings: (
        DatabaseSettings
        | RedisCacheSettings
        | AppSettings
        | ClientSideCacheSettings
        | RedisQueueSettings
        | EnvironmentSettings
    ),
    create_tables_on_start: bool = True,
) -> Callable[[FastAPI], contextlib._AsyncGeneratorContextManager[Any]]:
    """Factory to create a lifespan async context manager for a FastAPI app."""

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator:
        from asyncio import Event

        initialization_complete = Event()
        app.state.initialization_complete = initialization_complete

        await set_threadpool_tokens()

        try:
            if isinstance(_settings, RedisCacheSettings):
                await create_redis_cache_pool()

            if isinstance(_settings, RedisQueueSettings):
                await create_redis_queue_pool()

            if create_tables_on_start:
                await create_tables()

            initialization_complete.set()

            yield

        finally:
            if isinstance(_settings, RedisCacheSettings):
                await close_redis_cache_pool()

            if isinstance(_settings, RedisQueueSettings):
                await close_redis_queue_pool()

    return lifespan


# -------------- application --------------
def create_application(
    router: APIRouter,
    lifespan: Callable[[FastAPI], contextlib._AsyncGeneratorContextManager[None]],
    _settings: (
        DatabaseSettings
        | RedisCacheSettings
        | AppSettings
        | ClientSideCacheSettings
        | RedisQueueSettings
        | EnvironmentSettings
    ),
    create_tables_on_start: bool = True,
    **kwargs: Any,
) -> FastAPI:
    """Creates and configures a FastAPI application based on the provided settings.

    This function initializes a FastAPI application and configures it with various settings
    and handlers based on the type of the `settings` object provided.

    Parameters
    ----------
    router : APIRouter
        The APIRouter object containing the routes to be included in the FastAPI application.

    _settings
        An instance representing the settings for configuring the FastAPI application.
        It determines the configuration applied:

        - AppSettings: Configures basic app metadata like name, description, contact, and license info.
        - DatabaseSettings: Adds event handlers for initializing database tables during startup.
        - RedisCacheSettings: Sets up event handlers for creating and closing a Redis cache pool.
        - ClientSideCacheSettings: Integrates middleware for client-side caching.
        - RedisQueueSettings: Sets up event handlers for creating and closing a Redis queue pool.
        - EnvironmentSettings: Conditionally sets documentation URLs and integrates custom routes for API documentation
          based on the environment type.

    create_tables_on_start : bool
        A flag to indicate whether to create database tables on application startup.
        Defaults to True.

    **kwargs
        Additional keyword arguments passed directly to the FastAPI constructor.

    Returns
    -------
    FastAPI
        A fully configured FastAPI application instance.

    The function configures the FastAPI application with different features and behaviors
    based on the provided settings. It includes setting up database connections, Redis pools
    for caching, queue, and rate limiting, client-side caching, and customizing the API documentation
    based on the environment settings.
    """
    # --- before creating application ---
    if isinstance(_settings, AppSettings):
        to_update = {
            "title": _settings.APP_NAME,
            "description": _settings.APP_DESCRIPTION,
            "contact": {"name": _settings.CONTACT_NAME, "email": _settings.CONTACT_EMAIL},
            "license_info": {"name": _settings.LICENSE_NAME},
        }
        kwargs.update(to_update)

    if isinstance(_settings, EnvironmentSettings):
        kwargs.update({"docs_url": None, "redoc_url": None, "openapi_url": None})

    # Use custom lifespan if provided, otherwise use default factory
    if lifespan is None:
        lifespan = lifespan_factory(_settings, create_tables_on_start=create_tables_on_start)

    # Create instance of FastAPI with the provided lifespan and additional settings
    application = FastAPI(lifespan=lifespan, **kwargs)

    # Include router in the application
    application.include_router(router)

    # --- Client-side cache middleware ---
    if isinstance(_settings, ClientSideCacheSettings):
        application.add_middleware(ClientCacheMiddleware, max_age=_settings.CLIENT_CACHE_MAX_AGE)  # type: ignore

    # --- CORS middleware ---
    if isinstance(_settings, CORSSettings):
        application.add_middleware(
            fastapi.middleware.cors.CORSMiddleware,
            allow_origins=_settings.CORS_ORIGINS,
            allow_credentials=_settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=_settings.CORS_ALLOW_METHODS,
            allow_headers=_settings.CORS_ALLOW_HEADERS,
        )

    # --- Documentation router in `Local`, `Staging` and `Production`  environments ---
    if isinstance(_settings, EnvironmentSettings):
        if _settings.ENVIRONMENT != EnvironmentOption.PRODUCTION:
            docs_router = APIRouter()
            if _settings.ENVIRONMENT != EnvironmentOption.LOCAL:
                docs_router = APIRouter(dependencies=[Depends(get_current_superuser)])

            @docs_router.get("/docs", include_in_schema=False)
            async def get_swagger_documentation() -> fastapi.responses.HTMLResponse:
                return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")

            @docs_router.get("/redoc", include_in_schema=False)
            async def get_redoc_documentation() -> fastapi.responses.HTMLResponse:
                return get_redoc_html(openapi_url="/openapi.json", title="docs")

            @docs_router.get("/openapi.json", include_in_schema=False)
            async def openapi() -> dict[str, Any]:
                out: dict = get_openapi(title=application.title, version=application.version, routes=application.routes)
                return out

            @docs_router.get("/health", include_in_schema=False)
            async def health_check() -> dict[str, str]:
                """Health check endpoint."""
                return {"status": "ok"}

            application.include_router(docs_router)

    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(Exception, internal_server_error_handler)
    return application


async def http_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Custom error handler for HTTP exceptions."""
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "message": exc.detail,
                "errors": [str(exc)],
                "status_code": exc.status_code,
                "status": "error",
            },
        )
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal Server Error",
            "errors": [str(exc)],
            "status_code": 500,
            "status": "error",
        },
    )


async def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Custom error handler for request validation errors."""
    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "message": "Validation Error",
                "errors": exc.errors(),
                "status_code": 422,
                "status": "error",
            },
        )
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal Server Error",
            "errors": [str(exc)],
            "status_code": 500,
            "status": "error",
        },
    )


async def internal_server_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Custom error handler for internal server errors."""
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal Server Error",
            "errors": [str(exc)],
            "status_code": 500,
            "status": "error",
        },
    )
