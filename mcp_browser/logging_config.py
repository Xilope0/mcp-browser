"""
Logging configuration for MCP Browser.
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


class ServerNameAdapter(logging.LoggerAdapter):
    """Add server name context to log messages."""
    
    def process(self, msg, kwargs):
        server = self.extra.get('server', 'main')
        return f"[{server}] {msg}", kwargs


def setup_logging(debug: bool = False, log_file: Optional[Path] = None, 
                  log_level: Optional[str] = None, use_syslog: bool = False):
    """
    Configure logging for MCP Browser.
    
    Args:
        debug: Enable debug logging
        log_file: Optional file to write logs to
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR)
        use_syslog: Use syslog instead of console/file (for server mode)
    """
    # Determine log level
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
    elif debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    # Create formatter
    if level == logging.DEBUG:
        # Include timestamp and module for debug
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Simpler format for normal use
        formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    if use_syslog:
        # Use syslog for server mode - NEVER write to stdout/stderr
        from logging.handlers import SysLogHandler
        try:
            # Try Unix socket first (most common on Linux)
            syslog_handler = SysLogHandler(
                facility=SysLogHandler.LOG_DAEMON,
                address='/dev/log'
            )
        except (OSError, FileNotFoundError):
            # Fall back to UDP socket (for macOS, some Linux distros)
            try:
                syslog_handler = SysLogHandler(
                    facility=SysLogHandler.LOG_DAEMON,
                    address=('localhost', 514)
                )
            except Exception:
                # If syslog is not available, log to a file instead
                import tempfile
                fallback_log = Path(tempfile.gettempdir()) / 'mcp-browser-server.log'
                file_handler = logging.FileHandler(fallback_log, mode='a')
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                return
        
        # Syslog has its own format, but we can prepend our app name
        syslog_formatter = logging.Formatter('mcp-browser[%(process)d]: %(name)s - %(levelname)s - %(message)s')
        syslog_handler.setFormatter(syslog_formatter)
        root_logger.addHandler(syslog_handler)
    elif log_file:
        # File handler if requested
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # Only add console handler if not logging to /dev/null
        if str(log_file) != '/dev/null':
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
    else:
        # Console handler (stderr) only if no file specified
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Set levels for specific loggers
    # Suppress some noisy libraries unless in debug mode
    if level > logging.DEBUG:
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name: str, server: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with optional server context.
    
    Args:
        name: Logger name (usually __name__)
        server: Optional server name for context
        
    Returns:
        Logger or LoggerAdapter with server context
    """
    logger = logging.getLogger(name)
    
    if server:
        return ServerNameAdapter(logger, {'server': server})
    
    return logger


class RawIOFilter(logging.Filter):
    """Filter to only show raw I/O at TRACE level (5)."""
    
    def filter(self, record):
        # Only show raw I/O messages at TRACE level
        return record.levelno <= 5 or not record.msg.startswith(('>>> ', '<<< '))


# Add custom TRACE level for raw I/O
TRACE = 5
logging.addLevelName(TRACE, 'TRACE')

def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)

# Add trace method to Logger class
logging.Logger.trace = trace