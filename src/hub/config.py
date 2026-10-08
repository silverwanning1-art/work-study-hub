"""Application settings, read from environment variables."""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets must be typed as ``SecretStr``."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = "INFO"
    plugins_dir: Path = Path("plugins")
    agents_dir: Path = Path("agents")
    anthropic_api_key: SecretStr | None = None
