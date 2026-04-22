from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocuParse API"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://docuparse:docuparse@localhost:5433/docuparse"
    upload_dir: Path = Path("uploads")
    backend_base_url: str = "http://localhost:8001"
    cors_origins: list[str] = ["http://localhost:3001"]
    max_upload_mb: int = 12
    ai_provider: str = "auto"
    ai_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    ai_primary_provider: str = "paddleocr_vl"
    ai_secondary_provider: str = "qwen2_5_vl"
    ai_enable_second_pass: bool = True
    ai_second_pass_confidence_threshold: float = 0.80
    ai_model_dir: Path = Path("models")
    paddleocr_vl_model_dir: Path | None = None
    paddleocr_vl_layout_model_dir: Path | None = None
    paddleocr_vl_hf_repo: str = "PaddlePaddle/PaddleOCR-VL-1.5"
    paddleocr_vl_device: str | None = "cpu"
    paddleocr_vl_engine: str | None = None
    qwen2_5_vl_model_name: str = "Qwen/Qwen2.5-VL-3B-Instruct"
    qwen2_5_vl_model_dir: Path | None = None
    qwen2_5_vl_device: str = "auto"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.ai_model_dir.mkdir(parents=True, exist_ok=True)
    return settings
