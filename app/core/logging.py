



import logging
import json
import sys
from datetime import datetime, timezone

class SecureJsonFormatter(logging.Formatter):
    """Structured JSON logs with automatic sensitive data filtering."""
    
    SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "refresh_token"}
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Attach request correlation ID if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
            
        # Attach exception traceback only for ERROR/CRITICAL
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging():
    """Configure application-wide structured logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(SecureJsonFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]
    
    # Suppress noisy third-party logs in production
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)