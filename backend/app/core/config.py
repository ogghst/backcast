from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    API_V1_STR: str
    PROJECT_NAME: str
    DEBUG: bool
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    PORT: int
    BACKEND_CORS_ORIGINS: list[str]
    BACKEND_CORS_METHODS: list[str]
    BACKEND_CORS_HEADERS: list[str]
    RBAC_POLICY_FILE: str

    # Provider configuration
    RBAC_PROVIDER: str = "json"  # "json" | "database" (future: "entra")
    AUTH_PROVIDER: str = "local"  # "local" | "oidc" (future)
    USER_PROVIDER: str = "local"  # "local" | "entra" | "hybrid" (future)

    # Database
    DATABASE_URL: PostgresDsn

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ASYNC_DATABASE_URI(self) -> PostgresDsn:
        return self.DATABASE_URL

    # Logging
    LOG_LEVEL: str
    LOG_FILE: str
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_MAX_BYTES: int = 50 * 1024  # 50 KB default
    LOG_BACKUP_COUNT: int = 10  # Keep up to 10 rotated log files

    # AI Token Buffering
    AI_TOKEN_BUFFER_ENABLED: bool = True
    AI_TOKEN_BUFFER_INTERVAL_MS: int = 1000  # 1 second default
    AI_TOKEN_BUFFER_MAX_SIZE: int = 10000  # Max tokens before forced flush

    # AI Approval Settings (used by BackcastSecurityMiddleware polling loop)
    AI_APPROVAL_TIMEOUT_SECONDS: float = 60.0
    AI_APPROVAL_POLL_INTERVAL_MS: float = 200.0
    AI_APPROVAL_HEARTBEAT_INTERVAL_SECONDS: float = 5.0

    # Refresh Token Configuration
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days default

    # OpenTelemetry
    OTEL_ENABLED: bool = False
    OTLP_ENDPOINT: str = "http://localhost:6006/v1/traces"

    # Telegram Notifications
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""


settings = Settings()
