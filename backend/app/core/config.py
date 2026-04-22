from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocuParse API"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://docuparse:docuparse@localhost:5432/docuparse"
    upload_dir: Path = Path("uploads")
    backend_base_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:3000"]
    max_upload_mb: int = 12

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
