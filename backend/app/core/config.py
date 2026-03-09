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


settings = Settings()
