"""
Configuration management for MCP Browser.

Handles loading and validation of MCP server configurations,
supporting hierarchical config loading and runtime overrides.
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

from .default_configs import ConfigManager


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    command: List[str]
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    name: Optional[str] = None
    description: Optional[str] = None
    

@dataclass
class MCPBrowserConfig:
    """Main configuration for MCP Browser."""
    servers: Dict[str, MCPServerConfig] = field(default_factory=dict)
    default_server: Optional[str] = None
    sparse_mode: bool = True
    debug: bool = False
    buffer_size: int = 65536
    timeout: float = 30.0
    enable_builtin_servers: bool = True


class ConfigLoader:
    """Loads and manages MCP Browser configuration."""
    
    DEFAULT_CONFIG = {
        "servers": {
            "default": {
                "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
                "name": "memory",
                "description": "Default in-memory MCP server"
            }
        },
        "default_server": "default",
        "sparse_mode": True,
        "debug": False,
        "enable_builtin_servers": True
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_manager = ConfigManager()
        
        # Use provided path or default config location
        if config_path:
            self.config_path = config_path
        else:
            # Ensure default config exists
            self.config_manager.ensure_config_directory()
            self.config_path = self.config_manager.get_config_path()
        
        self._config: Optional[MCPBrowserConfig] = None
    
    
    def load(self) -> MCPBrowserConfig:
        """Load configuration from file or use defaults."""
        if self._config:
            return self._config
        
        config_data = self.DEFAULT_CONFIG.copy()
        
        if self.config_path and self.config_path.exists():
            with open(self.config_path) as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    self._merge_configs(config_data, file_config)
        
        # Convert to dataclass instances
        servers = {}
        for name, server_config in config_data.get("servers", {}).items():
            servers[name] = MCPServerConfig(
                command=server_config["command"],
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
                name=server_config.get("name", name),
                description=server_config.get("description")
            )
        
        self._config = MCPBrowserConfig(
            servers=servers,
            default_server=config_data.get("default_server"),
            sparse_mode=config_data.get("sparse_mode", True),
            debug=config_data.get("debug", False),
            buffer_size=config_data.get("buffer_size", 65536),
            timeout=config_data.get("timeout", 30.0),
            enable_builtin_servers=config_data.get("enable_builtin_servers", True)
        )
        
        return self._config
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Merge override config into base config."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value