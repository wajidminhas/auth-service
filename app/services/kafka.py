# app/services/kafka.py

import json
import logging
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """Singleton Kafka producer — one connection shared across all requests."""

    _producer: KafkaProducer = None

    @classmethod
    def get_producer(cls) -> KafkaProducer:
        """Return existing producer or create new one."""
        if cls._producer is None:
            try:
                cls._producer = KafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    key_serializer=lambda k: k.encode("utf-8") if k else None,
                    acks="all",
                    retries=3,
                    retry_backoff_ms=100,
                    request_timeout_ms=10000,
                )
                logger.info("Kafka producer connected")
            except NoBrokersAvailable:
                logger.warning("Kafka unavailable — events will not be published")
                return None
            except Exception as e:
                logger.error(f"Kafka connection error: {e}")
                return None
        return cls._producer

    @classmethod
    def publish(cls, topic: str, event: dict, key: str = None) -> bool:
        """Publish event to Kafka topic. Returns True if successful."""
        producer = cls.get_producer()
        if producer is None:
            logger.warning(f"Skipping event — Kafka unavailable: {event}")
            return False
        try:
            event["timestamp"] = datetime.now(timezone.utc).isoformat()
            future = producer.send(topic=topic, value=event, key=key)
            producer.flush()
            record = future.get(timeout=10)
            logger.info(
                f"Event published | topic={record.topic} "
                f"partition={record.partition} "
                f"offset={record.offset} "
                f"type={event['event_type']}"
            )
            return True
        except KafkaError as e:
            logger.error(f"Kafka publish error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected publish error: {e}")
            return False

    @classmethod
    def close(cls) -> None:
        """Flush and close Kafka producer gracefully."""
        if cls._producer is not None:
            cls._producer.flush()
            cls._producer.close()
            cls._producer = None
            logger.info("Kafka producer closed")


def _publish(event_type: str, user_id: int, email: str, extra: dict = None) -> None:
    """Internal helper — builds and publishes standardized event."""
    event = {"event_type": event_type, "user_id": user_id, "email": email}
    if extra:
        event.update(extra)
    KafkaEventProducer.publish(
        topic=settings.KAFKA_TOPIC,
        event=event,
        key=email
    )


# ─── Auth Events ──────────────────────────────────────────────────

def publish_user_registered(user_id: int, email: str, username: str) -> None:
    """Publish event when new user registers successfully."""
    _publish("user_registered", user_id, email, {"username": username})


def publish_user_logged_in(user_id: int, email: str) -> None:
    """Publish event when user logs in successfully."""
    _publish("user_logged_in", user_id, email)


def publish_user_logged_out(user_id: int, email: str) -> None:
    """Publish event when user logs out."""
    _publish("user_logged_out", user_id, email)


def publish_user_deactivated(user_id: int, email: str) -> None:
    """Publish event when user account is deactivated."""
    _publish("user_deactivated", user_id, email)


# ─── Password Events ──────────────────────────────────────────────

def publish_password_changed(user_id: int, email: str) -> None:
    """Publish event when user changes password."""
    _publish("password_changed", user_id, email)


def publish_password_reset_requested(user_id: int, email: str) -> None:
    """Publish event when user requests password reset OTP."""
    _publish("password_reset_requested", user_id, email)


def publish_password_reset_completed(user_id: int, email: str) -> None:
    """Publish event when user successfully resets password."""
    _publish("password_reset_completed", user_id, email)


# ─── Token Events ─────────────────────────────────────────────────

def publish_token_refreshed(user_id: int, email: str) -> None:
    """Publish event when user refreshes access token."""
    _publish("token_refreshed", user_id, email)


# ─── Profile Events ───────────────────────────────────────────────

def publish_profile_updated(user_id: int, email: str) -> None:
    """Publish event when user updates profile information."""
    _publish("profile_updated", user_id, email)