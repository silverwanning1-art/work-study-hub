"""Plugin settings, read from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration of the invoice plugin."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    invoice_db_path: str = "/data/invoice.sqlite"
    log_level: str = "INFO"
