

# app/services/kafka.py

import json
import logging
from datetime import datetime, timezone
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaEventProducer:
    """
    Kafka Producer for Auth Service.
    
    This class is responsible for publishing events to Kafka.
    Uses Singleton pattern — only one producer instance exists.
    One connection shared across all requests = efficient.
    """

    # Class level variable — shared across all instances
    # None means producer not created yet
    _producer: KafkaProducer = None

    @classmethod
    def get_producer(cls) -> KafkaProducer:
        """
        Returns existing producer or creates new one.
        
        Singleton pattern:
            First call  → creates producer → stores in _producer
            Second call → _producer exists → returns same one
            Third call  → _producer exists → returns same one
        
        Why Singleton?
            Creating Kafka connection is expensive operation.
            We do it once and reuse forever.
            Like keeping one phone line open instead of
            calling and hanging up for every message.
        """
        if cls._producer is None:
            try:
                cls._producer = KafkaProducer(
                    # Where is our Kafka broker running?
                    # In Docker it will be kafka:9092
                    # locally it is localhost:9092
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,

                    # Kafka sends raw bytes — not Python dicts
                    # This serializer converts our dict to JSON bytes automatically
                    # lambda v means: for every value v, do this conversion
                    # json.dumps converts dict to JSON string
                    # .encode converts string to bytes
                    # Example: {"event": "login"} → b'{"event": "login"}'
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),

                    # Also serialize the key to bytes
                    # Key is used to determine which partition message goes to
                    # Same key always goes to same partition
                    # This ensures ordered processing per user
                    key_serializer=lambda k: k.encode("utf-8") if k else None,

                    # acks means acknowledgement
                    # "all" means wait for ALL replicas to confirm receipt
                    # This is the safest setting — no data loss
                    # "0" = fire and forget (fastest but risky)
                    # "1" = wait for leader only (middle ground)
                    # "all" = wait for all replicas (safest)
                    acks="all",

                    # If sending fails — retry 3 times before giving up
                    retries=3,

                    # Wait 100ms between retries
                    retry_backoff_ms=100,

                    # If Kafka is not available at startup
                    # wait maximum 10 seconds before giving up
                    request_timeout_ms=10000,
                )
                logger.info("Kafka producer connected successfully")

            except NoBrokersAvailable:
                # Kafka is not running — log warning but dont crash app
                # Auth service should work even if Kafka is temporarily down
                logger.warning(
                    "Kafka broker not available. "
                    "Events will not be published until Kafka is running."
                )
                return None

            except Exception as e:
                logger.error(f"Unexpected error connecting to Kafka: {e}")
                return None

        return cls._producer

    @classmethod
    def publish(cls, topic: str, event: dict, key: str = None) -> bool:
        """
        Publishes a single event to specified Kafka topic.
        
        What happens internally:
            1. Get or create producer connection
            2. Send event to Kafka broker
            3. Broker stores event in topic partition
            4. Broker confirms receipt (because acks="all")
            5. flush() ensures message actually sent not just buffered
        
        Args:
            topic: Which Kafka topic to publish to
                   Example: "auth-events"
            event: Dictionary containing event data
                   Example: {"event_type": "user_registered", "user_id": 1}
            key:   Optional partition key
                   Using user email as key ensures all events
                   for same user go to same partition
                   This guarantees ordered processing per user
        
        Returns:
            True if published successfully
            False if publishing failed
        """
        producer = cls.get_producer()

        # If producer is None Kafka is not available
        # Return False but do not crash the application
        if producer is None:
            logger.warning(f"Skipping event publish — Kafka unavailable: {event}")
            return False

        try:
            # Add timestamp to every event automatically
            # So consumers know exactly when event happened
            event["timestamp"] = datetime.now(timezone.now).isoformat()

            # Send event to Kafka
            # This is async internally — goes to buffer first
            future = producer.send(
                topic=topic,
                value=event,
                key=key
            )

            # flush() forces all buffered messages to actually send
            # Without flush() messages might stay in buffer
            # and never reach Kafka broker
            producer.flush()

            # Get result of send operation
            # This confirms broker received our message
            record_metadata = future.get(timeout=10)

            logger.info(
                f"Event published successfully | "
                f"Topic: {record_metadata.topic} | "
                f"Partition: {record_metadata.partition} | "
                f"Offset: {record_metadata.offset} | "
                f"Event: {event['event_type']}"
            )
            return True

        except KafkaError as e:
            # Kafka specific error — broker issue, network issue etc
            logger.error(f"Kafka error publishing event: {e}")
            return False

        except Exception as e:
            # Any other unexpected error
            logger.error(f"Unexpected error publishing event: {e}")
            return False

    @classmethod
    def close(cls) -> None:
        """
        Gracefully closes Kafka producer connection.
        Called when application shuts down.
        
        Why graceful shutdown?
            Without this — buffered messages might be lost
            With this — all pending messages sent before closing
        """
        if cls._producer is not None:
            # flush() sends any remaining buffered messages
            cls._producer.flush()
            cls._producer.close()
            cls._producer = None
            logger.info("Kafka producer closed gracefully")


# ─── Event Publisher Functions ────────────────────────────────────────────────
# These are clean simple functions that routes and services call
# They hide Kafka complexity from rest of the application
# Rest of app just calls publish_user_registered() — simple!

def publish_user_registered(user_id: int, email: str, username: str) -> None:
    """
    Publishes event when new user registers.
    
    Who listens to this event in future?
        - Email Service     → sends welcome email
        - Analytics Service → tracks new signups
        - Notification Service → sends welcome SMS
    
    Event published to Kafka:
        {
            "event_type": "user_registered",
            "user_id": 1,
            "email": "john@example.com",
            "username": "john_doe",
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    event = {
        "event_type": "user_registered",
        "user_id": user_id,
        "email": email,
        "username": username,
    }
    # Use email as key so all events for same user
    # go to same Kafka partition — ordered processing
    KafkaEventProducer.publish(
        topic=settings.KAFKA_TOPIC,
        event=event,
        key=email
    )


def publish_user_logged_in(user_id: int, email: str) -> None:
    """
    Publishes event when user logs in successfully.
    
    Who listens to this event in future?
        - Analytics Service  → tracks login activity
        - Security Service   → monitors suspicious logins
        - Notification Service → alerts on new device login
    
    Event published to Kafka:
        {
            "event_type": "user_logged_in",
            "user_id": 1,
            "email": "john@example.com",
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    event = {
        "event_type": "user_logged_in",
        "user_id": user_id,
        "email": email,
    }
    KafkaEventProducer.publish(
        topic=settings.KAFKA_TOPIC,
        event=event,
        key=email
    )


def publish_user_deactivated(user_id: int, email: str) -> None:
    """
    Publishes event when user account is deactivated.
    
    Who listens to this event in future?
        - Email Service  → sends account deactivation email
        - Session Service → invalidates all active sessions
    
    Event published to Kafka:
        {
            "event_type": "user_deactivated",
            "user_id": 1,
            "email": "john@example.com",
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    event = {
        "event_type": "user_deactivated",
        "user_id": user_id,
        "email": email,
    }
    KafkaEventProducer.publish(
        topic=settings.KAFKA_TOPIC,
        event=event,
        key=email
    )