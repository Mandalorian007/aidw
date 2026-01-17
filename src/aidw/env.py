"""Configuration loading for AIDW.

Follows the aitk pattern: env → credentials file → config file chain.
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
CREDENTIALS_FILE = CONFIG_DIR / "credentials"
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

    # Credentials (loaded via get_credential)
    webhook_secret: str = Field(default="")
    e2b_api_key: str = Field(default="")
    gh_token: str = Field(default="")
    claude_token: str = Field(default="")  # Long-lived Claude Code token

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


def load_credentials_file() -> dict[str, str]:
    """Load credentials from file."""
    if not CREDENTIALS_FILE.exists():
        return {}

    creds = {}
    with open(CREDENTIALS_FILE) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line:
                key, value = line.split("=", 1)
                creds[key.strip()] = value.strip()
    return creds


def get_credential(key: str) -> str:
    """Get a credential by key.

    Checks in order: environment variable → credentials file.
    """
    # Check environment first
    value = os.getenv(key)
    if value:
        return value

    # Check credentials file
    creds = load_credentials_file()
    return creds.get(key, "")


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

    # Get credentials from environment or credentials file
    settings = Settings(
        webhook_secret=get_credential("AIDW_WEBHOOK_SECRET"),
        e2b_api_key=get_credential("E2B_API_KEY"),
        gh_token=get_credential("GH_TOKEN"),
        claude_token=get_credential("CLAUDE_CODE_TOKEN"),
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
    if not settings.claude_token:
        missing.append("CLAUDE_CODE_TOKEN (run: claude setup-token)")

    return missing
