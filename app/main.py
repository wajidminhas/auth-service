# app/main.py

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uuid

from app.database import create_db_and_tables
from app.routes.auth import router
from app.services.kafka import KafkaEventProducer
from app.services.redis import RedisClient
from app.core.config import settings
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import setup_logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)







@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME}")
    create_db_and_tables()
    KafkaEventProducer.get_producer()
    RedisClient.get_client()
    logger.info(f"{settings.APP_NAME} ready")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")
    KafkaEventProducer.close()
    RedisClient.close()


app = FastAPI(
    title=settings.APP_NAME,
    description="Production ready Authentication Microservice — FastAPI + Kafka + PostgreSQL + Redis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ─── INSERT NEW: Logging Setup ───────────────────────────────────
setup_logging()

# ─── INSERT NEW: Request ID Middleware ───────────────────────────
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)  # ← Await and capture
        response.headers["X-Request-Id"] = request.state.request_id
        return response  # ← MUST return the response object

app.add_middleware(RequestIdMiddleware)


logger = logging.getLogger(__name__)


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
    return JSONResponse(  # ← MUST return JSONResponse, never None
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
    return JSONResponse(  # ← MUST return JSONResponse, never None
        status_code=500,
        content={"error": "internal_server_error"}
    )


app.include_router(router)


@app.get("/", tags=["Root"])
def root():
    """Service info and documentation links."""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }