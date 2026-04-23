

# app/main.py

import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.services.redis import RedisClient
from app.database import create_db_and_tables
from app.routes.auth import router
from app.services.kafka import KafkaEventProducer
from app.core.config import settings


# ─── Logging Setup ────────────────────────────────────────────────
# Configure logging for entire application
# Every file uses logger = logging.getLogger(__name__)
# This config applies to all of them
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)



# Update lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):

    # Startup
    logger.info(f"Starting {settings.APP_NAME}...")
    create_db_and_tables()
    logger.info("Database tables created successfully")
    KafkaEventProducer.get_producer()
    logger.info("Kafka producer initialized")
    RedisClient.get_client()          # ← add this
    logger.info("Redis initialized")  # ← add this
    logger.info(f"{settings.APP_NAME} started successfully!")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    KafkaEventProducer.close()
    RedisClient.close()               # ← add this
    logger.info(f"{settings.APP_NAME} shutdown complete")


# ─── FastAPI App ──────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="Production ready Authentication Microservice with FastAPI, Kafka and PostgreSQL",
    lifespan=lifespan
)


# ─── Register Routes ──────────────────────────────────────────────
# Include auth router — all routes prefixed with /auth
app.include_router(router)


# ─── Root Endpoint ────────────────────────────────────────────────
@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.APP_NAME,
        
    }