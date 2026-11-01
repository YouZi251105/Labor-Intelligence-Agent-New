from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Labor Intelligence Agent"
    app_version: str = "0.2.0"
    app_env: str = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "dev-only-change-me"

    database_url: str = "sqlite+aiosqlite:///./data/demo.db"
    redis_url: str = "redis://localhost:6379/0"
    demo_seed: bool = True
    qianwen_api_key: str = ""
    qianwen_model: str = "qwen-plus"
    upload_dir: str = "./data/uploads"
    storage_backend: str = "local"
    task_backend: str = "inline"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "labor-minio"
    minio_secret_key: str = "labor_minio_password"
    minio_bucket: str = "labor-evidence"
    minio_secure: bool = False
    trusted_hosts: list[str] = ["*"]
    rate_limit_per_minute: int = 300
    enable_metrics: bool = True

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", PROJECT_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
