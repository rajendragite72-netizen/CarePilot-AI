from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    APP_NAME: str = "CarePilot AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DATABASE_URL: str = "sqlite:///./carepilot.db"

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    MAX_PDF_PAGES: int = 50

    AI_PROVIDER: str = "demo"
    NEMOTRON_API_URL: str = "https://integrate.api.nvidia.com/v1/chat/completions"
    NEMOTRON_API_KEY: Optional[str] = None
    NEMOTRON_MODEL: str = "nvidia/nemotron-3-ultra"

    DEMO_MODE: bool = True
    DEMO_AI_RESPONSE_DELAY_MS: int = 500

    CORS_ORIGINS_RAW: str = "http://localhost:8000,http://127.0.0.1:8000"
    SESSION_COOKIE_SECURE: bool = False
    CSRF_SECRET: str = "dev-csrf-secret-change-in-production"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS_RAW.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)