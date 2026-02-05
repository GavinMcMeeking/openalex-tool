"""
Configuration manager for OpenAlex CLI tool.
Handles saving and loading user preferences like email address.
"""

import json
import os
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path.home() / ".openalex-tool"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config_dir() -> Path:
    """Get the configuration directory, creating it if needed."""
    CONFIG_DIR.mkdir(exist_ok=True)
    return CONFIG_DIR


def load_config() -> dict:
    """
    Load configuration from file.

    Returns:
        Dictionary with configuration values
    """
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_config(config: dict) -> None:
    """
    Save configuration to file.

    Args:
        config: Dictionary with configuration values
    """
    get_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_email() -> Optional[str]:
    """
    Get the configured email address.

    Returns:
        Email address from config, or None if not configured
    """
    config = load_config()
    return config.get("email")


def set_email(email: str) -> None:
    """
    Set the email address in configuration.

    Args:
        email: Email address to save
    """
    config = load_config()
    config["email"] = email
    save_config(config)
    print(f"✓ Email configured: {email}")


def get_config_path() -> str:
    """Get the path to the config file for display purposes."""
    return str(CONFIG_FILE)
