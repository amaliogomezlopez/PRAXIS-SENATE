"""
Configuration utilities
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


def _load_env():
    """Load .env file from project root"""
    env_paths = [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent.parent.parent / ".env",
        Path(__file__).parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break


# Load environment variables from .env file
_load_env()


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    if config_path is None:
        config_path = Path(__file__).parent / "providers.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Expand environment variables
    config = _expand_env_vars(config)

    return config


def _expand_env_vars(obj: Any) -> Any:
    """Recursively expand environment variables in config"""
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_env_vars(item) for item in obj]
    elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        env_var = obj[2:-1]
        return os.environ.get(env_var, "")
    else:
        return obj
