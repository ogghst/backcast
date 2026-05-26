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
    # Provider configuration
    RBAC_PROVIDER: str = "database"  # "database" | "entra" (future)
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
    AI_TOKEN_BUFFER_INTERVAL_MS: int = 2000  # 2 seconds default
    AI_TOKEN_BUFFER_MAX_SIZE: int = 10000  # Max tokens before forced flush

    # AI Approval Settings (used by BackcastSecurityMiddleware polling loop)
    AI_APPROVAL_TIMEOUT_SECONDS: float = 60.0
    AI_APPROVAL_POLL_INTERVAL_MS: float = 200.0
    AI_APPROVAL_HEARTBEAT_INTERVAL_SECONDS: float = 5.0

    # Specialist retry (transient API errors)
    AI_SPECIALIST_MAX_RETRIES: int = 3

    # Refresh Token Configuration
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days default

    # OpenTelemetry
    OTEL_ENABLED: bool = False
    OTLP_ENDPOINT: str = "http://localhost:6006/v1/traces"

    # Cost Registration Attachments
    COST_REGISTRATION_MAX_ATTACHMENT_SIZE_MB: int = 10  # 10MB default

    # RustFS / S3 Storage
    RUSTFS_ENDPOINT_URL: str = "http://rustfs:9000"
    RUSTFS_ACCESS_KEY: str = "rustfsadmin"
    RUSTFS_SECRET_KEY: str = "rustfsadmin"
    RUSTFS_BUCKET_NAME: str = "backcast-documents"
    RUSTFS_PRESIGNED_URL_EXPIRY_SECONDS: int = 900  # 15 minutes

    # Document Repository
    DOCUMENT_MAX_FILE_SIZE_MB: int = 50
    DOCUMENT_MAX_STORAGE_PER_PROJECT_MB: int = 10240  # 10 GB
    DOCUMENT_ALLOWED_EXTENSIONS: list[str] = [
        "pdf",
        "docx",
        "xlsx",
        "pptx",
        "txt",
        "csv",
        "md",
        "png",
        "jpg",
        "jpeg",
        "gif",
        "webp",
        "svg",
        "dwg",
        "dxf",
        "step",
        "igs",
        "zip",
        "rar",
    ]

    # Telegram Notifications
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""


settings = Settings()
