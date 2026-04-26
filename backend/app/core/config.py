from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pydantic_settings.sources import (
    DotEnvSettingsSource,
    EnvSettingsSource,
    InitSettingsSource,
    PydanticBaseSettingsSource,
)


class Settings(BaseSettings):
    APP_NAME: str = "Smart DevOps Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    allowed_origins: list[str] = Field(
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        env="ALLOWED_ORIGINS",
    )

    DATABASE_URL: str
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    DEFAULT_LLM_PROVIDER: str = "ollama"
    DEFAULT_MODEL: str = "llama3.1:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    GITHUB_TOKEN: str | None = None
    GITHUB_WEBHOOK_SECRET: str | None = None

    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_DEFAULT_REGION: str = "us-east-1"

    DOCKER_HOST: str = "unix:///var/run/docker.sock"

    AGENT_MAX_ITERATIONS: int = 10
    AGENT_TIMEOUT_SECONDS: int = 120
    HITL_APPROVAL_TIMEOUT_SECONDS: int = 300
    ENABLE_HITL: bool = True

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    AUDIT_LOG_RETENTION_DAYS: int = 90

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: InitSettingsSource,
        env_settings: EnvSettingsSource,
        dotenv_settings: DotEnvSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )


settings = Settings()
