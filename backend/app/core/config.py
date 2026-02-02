import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment-specific .env file
# Environment files are located in project root (parent of backend/ directory)
environment = os.getenv("ENVIRONMENT", "development")
env_file = f".env.{environment}"

# Search for env file in multiple locations (in order)
# 1. Parent directory (project root) - preferred location for Docker Compose
# 2. Current directory (e.g., backend/) - for standalone backend usage
# 3. Fallback to .env for backwards compatibility
env_paths = [
    Path(__file__).parent.parent.parent.parent / env_file,  # Project root (backend/app/core/config.py -> up 4 levels)
    Path(env_file),                                            # Current directory
    Path(".env")                                               # Fallback
]

loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        loaded = True
        break

if not loaded:
    # No env file found - will use defaults or fail on required vars
    pass


class Settings(BaseSettings):
    # Find the actual env file path that was loaded
    _env_file_path = next(
        (p for p in env_paths if p.exists()),
        Path(".env")  # fallback
    )

    model_config = SettingsConfigDict(
        env_file=str(_env_file_path),
        env_ignore_empty=True,
        extra="ignore",
    )

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Backcast EVS"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    PORT: int = 8020
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    BACKEND_CORS_METHODS: list[str] = ["*"]
    BACKEND_CORS_HEADERS: list[str] = ["*"]

    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        """Convert CORS origins string to list."""
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
    RBAC_POLICY_FILE: str = "config/rbac.json"

    # Database
    DATABASE_URL: PostgresDsn

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ASYNC_DATABASE_URI(self) -> PostgresDsn:
        return self.DATABASE_URL

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


settings = Settings()
