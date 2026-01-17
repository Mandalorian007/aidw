"""Configuration loading for AIDW.

Follows the aitk pattern: env → config file → .env chain.
"""

import os
from pathlib import Path
from functools import lru_cache

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Config directory
CONFIG_DIR = Path.home() / ".aidw"
CONFIG_FILE = CONFIG_DIR / "config.yml"
DB_FILE = CONFIG_DIR / "sessions.db"


class ServerConfig(BaseSettings):
    """Server configuration."""

    port: int = Field(default=8787, description="Server port")
    workers: int = Field(default=3, description="Number of workers")
    host: str = Field(default="0.0.0.0", description="Server host")


class GitHubConfig(BaseSettings):
    """GitHub configuration."""

    bot_name: str = Field(default="aidw", description="Bot trigger name")


class AuthConfig(BaseSettings):
    """Authentication configuration."""

    allowed_users: list[str] = Field(default_factory=list, description="Allowed GitHub usernames")


class Settings(BaseSettings):
    """Main settings class combining all configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AIDW_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Credentials from environment
    webhook_secret: str = Field(default="", alias="AIDW_WEBHOOK_SECRET")
    e2b_api_key: str = Field(default="", alias="E2B_API_KEY")
    gh_token: str = Field(default="", alias="GH_TOKEN")

    # Nested configs (loaded from file)
    server: ServerConfig = Field(default_factory=ServerConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)


def load_config_file() -> dict:
    """Load configuration from YAML file."""
    if not CONFIG_FILE.exists():
        return {}

    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f) or {}


def ensure_config_dir() -> None:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def create_default_config() -> None:
    """Create default config file if it doesn't exist."""
    ensure_config_dir()
    if CONFIG_FILE.exists():
        return

    default_config = {
        "server": {
            "port": 8787,
            "workers": 3,
        },
        "github": {
            "bot_name": "aidw",
        },
        "auth": {
            "allowed_users": [],
        },
    }

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Loads from environment variables first, then config file.
    """
    # Load config file
    config_data = load_config_file()

    # Build nested configs from file
    server_config = ServerConfig(**config_data.get("server", {}))
    github_config = GitHubConfig(**config_data.get("github", {}))
    auth_config = AuthConfig(**config_data.get("auth", {}))

    # Get credentials from environment
    settings = Settings(
        webhook_secret=os.getenv("AIDW_WEBHOOK_SECRET", ""),
        e2b_api_key=os.getenv("E2B_API_KEY", ""),
        gh_token=os.getenv("GH_TOKEN", ""),
        server=server_config,
        github=github_config,
        auth=auth_config,
    )

    return settings


def validate_required_credentials() -> list[str]:
    """Check for required credentials and return list of missing ones."""
    settings = get_settings()
    missing = []

    if not settings.webhook_secret:
        missing.append("AIDW_WEBHOOK_SECRET")
    if not settings.e2b_api_key:
        missing.append("E2B_API_KEY")
    if not settings.gh_token:
        missing.append("GH_TOKEN")

    return missing
