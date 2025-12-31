"""
Advanced logging configuration with structured logging
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Any
import structlog
from datetime import datetime
import json
import os

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'ip_address'):
            log_entry["ip_address"] = record.ip_address
        if hasattr(record, 'endpoint'):
            log_entry["endpoint"] = record.endpoint
        if hasattr(record, 'method'):
            log_entry["method"] = record.method
        if hasattr(record, 'status_code'):
            log_entry["status_code"] = record.status_code
        if hasattr(record, 'response_time'):
            log_entry["response_time"] = record.response_time
        
        return json.dumps(log_entry, ensure_ascii=False)

class LoggingConfig:
    """Centralized logging configuration"""
    
    def __init__(self, log_level: str = "INFO", log_dir: str = "logs"):
        self.log_level = getattr(logging, log_level.upper())
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Configure structlog
        self._configure_structlog()
        
        # Configure standard logging
        self._configure_standard_logging()
    
    def _configure_structlog(self):
        """Configure structlog for structured logging"""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def _configure_standard_logging(self):
        """Configure standard Python logging"""
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handlers
        self._setup_file_handlers(root_logger)
        
        # Configure specific loggers
        self._configure_specific_loggers()
    
    def _setup_file_handlers(self, root_logger: logging.Logger):
        """Setup rotating file handlers"""
        
        # General application log
        app_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        app_handler.setLevel(self.log_level)
        app_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(app_handler)
        
        # Error log
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "error.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(error_handler)
        
        # Access log
        access_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "access.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=7
        )
        access_handler.setLevel(logging.INFO)
        access_handler.setFormatter(JSONFormatter())
        
        # Create access logger
        access_logger = logging.getLogger("access")
        access_logger.addHandler(access_handler)
        access_logger.setLevel(logging.INFO)
        access_logger.propagate = False
        
        # Security log
        security_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / "security.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        security_handler.setLevel(logging.WARNING)
        security_handler.setFormatter(JSONFormatter())
        
        # Create security logger
        security_logger = logging.getLogger("security")
        security_logger.addHandler(security_handler)
        security_logger.setLevel(logging.WARNING)
        security_logger.propagate = False
    
    def _configure_specific_loggers(self):
        """Configure specific loggers with appropriate levels"""
        
        # SQLAlchemy - reduce verbosity
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
        
        # Uvicorn
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.INFO)
        
        # FastAPI
        logging.getLogger("fastapi").setLevel(logging.INFO)
        
        # Asyncio
        logging.getLogger("asyncio").setLevel(logging.WARNING)

class RequestLogger:
    """Request logging utility"""
    
    def __init__(self):
        self.access_logger = logging.getLogger("access")
        self.security_logger = logging.getLogger("security")
    
    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        ip_address: str,
        user_agent: str = "",
        user_id: str = "",
        request_id: str = ""
    ):
        """Log HTTP request"""
        
        extra = {
            "method": method,
            "endpoint": path,
            "status_code": status_code,
            "response_time": response_time,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "user_id": user_id,
            "request_id": request_id
        }
        
        message = f"{method} {path} - {status_code} - {response_time:.3f}s"
        
        if status_code >= 500:
            self.access_logger.error(message, extra=extra)
        elif status_code >= 400:
            self.access_logger.warning(message, extra=extra)
        else:
            self.access_logger.info(message, extra=extra)
    
    def log_security_event(
        self,
        event_type: str,
        message: str,
        ip_address: str,
        user_id: str = "",
        severity: str = "WARNING",
        **kwargs
    ):
        """Log security-related events"""
        
        extra = {
            "event_type": event_type,
            "ip_address": ip_address,
            "user_id": user_id,
            "severity": severity,
            **kwargs
        }
        
        log_message = f"Security Event: {event_type} - {message}"
        
        if severity == "CRITICAL":
            self.security_logger.critical(log_message, extra=extra)
        elif severity == "ERROR":
            self.security_logger.error(log_message, extra=extra)
        else:
            self.security_logger.warning(log_message, extra=extra)

# Global instances
logging_config = LoggingConfig(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_dir=os.getenv("LOG_DIR", "logs")
)

request_logger = RequestLogger()

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)