#!/usr/bin/env python3
"""
MCP Browser Daemon - Socket server for MCP Browser.

This daemon provides a persistent MCP Browser instance that clients can connect to.
"""

import os
import sys
import asyncio
import argparse
import signal
from pathlib import Path
from typing import Optional

from .proxy import MCPBrowser
from .daemon import MCPBrowserDaemon, get_socket_path
from .logging_config import setup_logging, get_logger


async def run_daemon(args):
    """Run the MCP Browser daemon."""
    logger = get_logger(__name__)
    
    # Create browser instance
    browser = MCPBrowser(
        server_name=args.server,
        config_path=Path(args.config) if args.config else None,
        enable_builtin_servers=not args.no_builtin
    )
    
    # Get socket path
    socket_path = get_socket_path(args.server)
    
    # Create and run daemon
    daemon = MCPBrowserDaemon(browser, socket_path)
    
    logger.info(f"Starting MCP Browser daemon on {socket_path}")
    
    try:
        await daemon.start()
    except KeyboardInterrupt:
        logger.info("Daemon shutting down...")
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        raise
    finally:
        await daemon.stop()


def handle_systemd_socket():
    """Check for systemd socket activation."""
    # Check if we're running under systemd with socket activation
    listen_pid = os.environ.get('LISTEN_PID')
    listen_fds = os.environ.get('LISTEN_FDS')
    
    if listen_pid and listen_fds and int(listen_pid) == os.getpid():
        # We have systemd socket activation
        num_fds = int(listen_fds)
        if num_fds > 0:
            # Use the first socket FD (SD_LISTEN_FDS_START = 3)
            return 3
    return None


def main():
    """Main entry point for daemon."""
    parser = argparse.ArgumentParser(
        description="MCP Browser Daemon - Persistent socket server",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--server", "-s", help="Target MCP server name")
    parser.add_argument("--config", "-c", help="Custom configuration file path")
    parser.add_argument("--no-builtin", action="store_true",
                       help="Disable built-in servers")
    parser.add_argument("--log-level", choices=["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level")
    parser.add_argument("--log-file", help="Log to file instead of stderr")
    parser.add_argument("--socket", help="Custom socket path (overrides default)")
    parser.add_argument("--foreground", "-f", action="store_true",
                       help="Run in foreground (don't daemonize)")
    parser.add_argument("--pid-file", help="Write PID to file")
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = Path(args.log_file) if args.log_file else None
    setup_logging(
        debug=args.log_level == "DEBUG",
        log_file=log_file,
        log_level=args.log_level
    )
    
    logger = get_logger(__name__)
    
    # Check for systemd socket activation
    systemd_fd = handle_systemd_socket()
    if systemd_fd:
        logger.info("Running with systemd socket activation")
        # TODO: Implement systemd socket handling
    
    # Handle PID file
    if args.pid_file:
        with open(args.pid_file, 'w') as f:
            f.write(str(os.getpid()))
    
    # Daemonize if not in foreground mode
    if not args.foreground:
        # Fork to background
        pid = os.fork()
        if pid > 0:
            # Parent process
            print(f"Started daemon with PID {pid}")
            sys.exit(0)
        
        # Child process continues
        os.setsid()
        
        # Redirect stdin/stdout/stderr
        with open(os.devnull, 'r') as devnull:
            os.dup2(devnull.fileno(), sys.stdin.fileno())
        with open(os.devnull, 'w') as devnull:
            os.dup2(devnull.fileno(), sys.stdout.fileno())
        if not args.log_file:
            os.dup2(devnull.fileno(), sys.stderr.fileno())
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(daemon.stop())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the daemon
    asyncio.run(run_daemon(args))


if __name__ == "__main__":
    main()