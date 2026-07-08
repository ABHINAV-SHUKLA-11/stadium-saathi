import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    DASHBOARD_PASSWORD: str = "stadium_saathi_admin_2026"
    DATABASE_URL: str = "sqlite+aiosqlite:///./stadium_saathi.db"
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173"
    ENVIRONMENT: str = "development"

    @field_validator("CORS_ORIGINS")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
