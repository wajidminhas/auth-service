

# app/main.py

import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

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


# ─── Lifespan ─────────────────────────────────────────────────────
# Lifespan handles startup and shutdown events
# Everything before yield runs on startup
# Everything after yield runs on shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):

    # ── Startup ──────────────────────────────────────────────────
    logger.info(f"Starting {settings.APP_NAME}...")

    # Create all database tables
    # SQLModel reads all models with table=True
    # and creates matching tables in PostgreSQL
    # If tables already exist — does nothing
    create_db_and_tables()
    logger.info("Database tables created successfully")

    # Initialize Kafka producer connection
    # This creates connection once at startup
    # All requests reuse this same connection
    KafkaEventProducer.get_producer()
    logger.info("Kafka producer initialized")

    logger.info(f"{settings.APP_NAME} started successfully!")

    yield  # Application runs here

    # ── Shutdown ─────────────────────────────────────────────────
    logger.info(f"Shutting down {settings.APP_NAME}...")

    # Close Kafka connection gracefully
    # Flushes remaining messages before closing
    KafkaEventProducer.close()
    logger.info("Kafka producer closed")

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