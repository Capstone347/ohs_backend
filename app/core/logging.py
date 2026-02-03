import json
import logging
from datetime import datetime
from typing import Any


class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        self.logger.error(message, extra=kwargs, exc_info=True)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        self.logger.warning(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(message, extra=kwargs)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "levelname", "levelno",
                "pathname", "filename", "module", "exc_info",
                "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "taskName"
            ]:
                log_data[key] = value
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
