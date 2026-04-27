# app/main.py

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database import create_db_and_tables
from app.routes.auth import router
from app.services.kafka import KafkaEventProducer
from app.services.redis import RedisClient
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)


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

app.include_router(router)


@app.get("/", tags=["Root"])
def root():
    """Service info and documentation links."""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }