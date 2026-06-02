"""Application configuration using Pydantic Settings."""
import json

from pydantic import field_validator

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return init_settings, env_settings, dotenv_settings, file_secret_settings

    # App
    APP_NAME: str = "Smart DevOps Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    DESKTOP_MODE: bool = False
    DISABLE_AUTH: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: str = ",".join(
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "capacitor://localhost",
            "http://localhost",
        ]
    )

    # Database
    # Supabase pooler example:
    # postgresql://postgres.<project-ref>:[YOUR-PASSWORD]@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres
    DATABASE_URL: str = "sqlite+aiosqlite:///./devops_assistant.db"
    DATABASE_SSL_VERIFY: bool = True

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    MEMORY_BACKEND: str = "auto"
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # Auth
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_NAME: str = "devops_access_token"

    # LLM
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_MODEL: str = "gpt-4o"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # GitHub
    GITHUB_TOKEN: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_REPO_FULL_NAME: str = ""
    GITHUB_APP_ID: str = ""
    GITHUB_APP_PRIVATE_KEY: str = ""
    GITHUB_APP_WEBHOOK_SECRET: str = ""
    GITHUB_APP_CLIENT_ID: str = ""
    GITHUB_APP_CLIENT_SECRET: str = ""

    # ML model artifacts
    FAILURE_MODEL_PATH: str = ""
    FIX_MAPPING_PATH: str = ""

    # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"

    # Agent
    AGENT_MAX_ITERATIONS: int = 10
    AGENT_TIMEOUT_SECONDS: int = 120
    HITL_APPROVAL_TIMEOUT_SECONDS: int = 300
    ENABLE_HITL: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    @property
    def auth_disabled(self) -> bool:
        """Whether local desktop mode should bypass JWT and RBAC checks."""
        return bool(self.DESKTOP_MODE or self.DISABLE_AUTH)

    @property
    def allowed_origins(self) -> list[str]:
        value = self.ALLOWED_ORIGINS.strip()
        if value.startswith("["):
            origins = json.loads(value)
            return [str(origin).strip() for origin in origins if str(origin).strip()]
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "off", "no"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "on", "yes"}:
                return True
        return value


settings = Settings()
