# app/services/kafka.py

import json
import logging
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaEventProducer:

    _producer: KafkaProducer = None

    @classmethod
    def get_producer(cls) -> KafkaProducer:
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
                logger.info("Kafka producer connected successfully")
            except NoBrokersAvailable:
                logger.warning("Kafka broker not available.")
                return None
            except Exception as e:
                logger.error(f"Unexpected error connecting to Kafka: {e}")
                return None
        return cls._producer

    @classmethod
    def publish(cls, topic: str, event: dict, key: str = None) -> bool:
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
                f"Event published | Topic: {record.topic} | "
                f"Partition: {record.partition} | "
                f"Offset: {record.offset} | "
                f"Type: {event['event_type']}"
            )
            return True
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False

    @classmethod
    def close(cls) -> None:
        if cls._producer is not None:
            cls._producer.flush()
            cls._producer.close()
            cls._producer = None
            logger.info("Kafka producer closed gracefully")


# ─── Helper to publish any event cleanly ─────────────────────────
def _publish(event_type: str, user_id: int, email: str, extra: dict = None) -> None:
    event = {
        "event_type": event_type,
        "user_id": user_id,
        "email": email,
    }
    if extra:
        event.update(extra)
    KafkaEventProducer.publish(
        topic=settings.KAFKA_TOPIC,
        event=event,
        key=email
    )


# ─── Auth Events ──────────────────────────────────────────────────

def publish_user_registered(user_id: int, email: str, username: str) -> None:
    # Fires when new user registers
    # Listeners: email service, analytics, notification service
    _publish("user_registered", user_id, email, {"username": username})


def publish_user_logged_in(user_id: int, email: str) -> None:
    # Fires when user logs in successfully
    # Listeners: analytics, security service
    _publish("user_logged_in", user_id, email)


def publish_user_logged_out(user_id: int, email: str) -> None:
    # Fires when user logs out
    # Listeners: analytics, session service
    _publish("user_logged_out", user_id, email)


def publish_user_deactivated(user_id: int, email: str) -> None:
    # Fires when user account is deactivated
    # Listeners: email service, session service
    _publish("user_deactivated", user_id, email)


# ─── Password Events ──────────────────────────────────────────────

def publish_password_changed(user_id: int, email: str) -> None:
    # Fires when user successfully changes password
    # Listeners: email service sends confirmation email
    _publish("password_changed", user_id, email)


def publish_password_reset_requested(user_id: int, email: str) -> None:
    # Fires when user requests password reset OTP
    # Listeners: email service sends OTP email
    _publish("password_reset_requested", user_id, email)


def publish_password_reset_completed(user_id: int, email: str) -> None:
    # Fires when user successfully resets password
    # Listeners: email service sends success confirmation
    _publish("password_reset_completed", user_id, email)


# ─── Token Events ─────────────────────────────────────────────────

def publish_token_refreshed(user_id: int, email: str) -> None:
    # Fires when user refreshes their token
    # Listeners: analytics, security monitoring
    _publish("token_refreshed", user_id, email)


# ─── Profile Events ───────────────────────────────────────────────

def publish_profile_updated(user_id: int, email: str) -> None:
    # Fires when user updates their profile
    # Listeners: analytics, notification service
    _publish("profile_updated", user_id, email)