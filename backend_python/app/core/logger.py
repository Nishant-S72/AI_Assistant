"""
Structured JSON logging configuration.
"""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from app.core.config import LOG_LEVEL, LOG_FORMAT


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "tier"):
            log_data["tier"] = record.tier
        if hasattr(record, "action"):
            log_data["action"] = record.action
        if hasattr(record, "intent"):
            log_data["intent"] = record.intent
        if hasattr(record, "confidence"):
            log_data["confidence"] = record.confidence
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logger(name: str = "app") -> logging.Logger:
    """Setup structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Add console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    if LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
    
    logger.addHandler(handler)
    return logger


# Global logger instance
logger = setup_logger()

