# app/main.py

import logging
import uuid
from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.database import create_db_and_tables
from app.routes.auth import router
from app.services.kafka import KafkaEventProducer
from app.services.redis import RedisClient

# ── 1. Logging first, before anything else ──────────────────────
setup_logging()
logger = logging.getLogger(__name__)


# ── 2. Middleware class defined before app ───────────────────────
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response


# ── 3. Lifespan — logger now exists when this runs ──────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}")
    await asyncio.get_event_loop().run_in_executor(None, create_db_and_tables)
    KafkaEventProducer.get_producer()
    RedisClient.get_client()
    logger.info(f"{settings.APP_NAME} ready")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")
    KafkaEventProducer.close()
    RedisClient.close()


# ── 4. App creation ──────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="Production ready Authentication Microservice — FastAPI + Kafka + PostgreSQL + Redis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ── 5. Middleware registration ───────────────────────────────────
app.add_middleware(RequestIdMiddleware)


# ── 6. Exception handlers ────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    level = logging.WARNING if exc.status_code < 500 else logging.ERROR
    logger.log(
        level,
        f"HTTP {exc.status_code} | {request.method} {request.url.path}",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "status_code": exc.status_code,
            "error_detail": exc.detail
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled server error",
        exc_info=exc,
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": request.url.path,
            "method": request.method
        }
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error"}
    )


# ── 7. Routers and root endpoint ─────────────────────────────────
app.include_router(router, prefix="/auth")  # All auth routes under /auth


@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }