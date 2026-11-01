from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, ORJSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import BACKEND_DIR, get_settings
from app.core.logging import configure_logging
from app.core.metrics import METRICS
from app.core.rate_limit import FixedWindowRateLimiter, RateLimitMiddleware
from app.db.session import initialize_database
from app.middleware.request_context import RequestContextMiddleware

settings = get_settings()
STATIC_DIR = Path(BACKEND_DIR) / "app" / "static"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.app_debug)
    await initialize_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.app_debug,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.trusted_hosts != ["*"]:
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )
app.add_middleware(
    RateLimitMiddleware,
    limiter=FixedWindowRateLimiter(settings.rate_limit_per_minute),
)
app.add_middleware(RequestContextMiddleware)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    if not settings.enable_metrics:
        return PlainTextResponse("metrics disabled", status_code=404)
    return PlainTextResponse(METRICS.render())


@app.get("/docs", include_in_schema=False)
async def local_swagger_ui() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.app_name} - API 文档",
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
        swagger_favicon_url="/static/swagger-ui/favicon-32x32.png",
        swagger_ui_parameters={
            "persistAuthorization": True,
            "displayRequestDuration": True,
        },
    )


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "service": "labor-intelligence-agent",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }
