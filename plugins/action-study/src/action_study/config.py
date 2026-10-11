"""Plugin settings, read from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration of the study plugin."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    study_db_path: str = "/data/study.sqlite"
    log_level: str = "INFO"
