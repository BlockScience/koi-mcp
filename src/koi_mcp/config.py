import json
import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class AgentConfig(BaseModel):
    name: str
    version: str = "1.0"
    base_url: str
    mcp_port: int
    traits: Dict[str, Any] = Field(default_factory=dict)

class NetworkConfig(BaseModel):
    first_contact: Optional[str] = None

class CoordinatorConfig(BaseModel):
    name: str
    base_url: str
    mcp_registry_port: int

class Config(BaseModel):
    agent: Optional[AgentConfig] = None
    coordinator: Optional[CoordinatorConfig] = None
    network: NetworkConfig = Field(default_factory=NetworkConfig)

def _deep_update(target, source):
    """Deep update a nested dictionary."""
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_update(target[key], value)
        else:
            target[key] = value

def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file or environment variables."""
    config = {}
    
    # Load from file if provided
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    
    # Check environment variables
    if os.getenv("KOI_MCP_CONFIG"):
        try:
            env_config = json.loads(os.getenv("KOI_MCP_CONFIG", "{}"))
            # Merge with existing config
            _deep_update(config, env_config)
        except json.JSONDecodeError:
            pass
    
    # Individual environment variables take precedence
    if os.getenv("KOI_MCP_AGENT_NAME"):
        if "agent" not in config:
            config["agent"] = {}
        config["agent"]["name"] = os.getenv("KOI_MCP_AGENT_NAME")
    
    if os.getenv("KOI_MCP_AGENT_BASE_URL"):
        if "agent" not in config:
            config["agent"] = {}
        config["agent"]["base_url"] = os.getenv("KOI_MCP_AGENT_BASE_URL")
    
    # More env vars can be added here
    
    return Config.model_validate(config)
