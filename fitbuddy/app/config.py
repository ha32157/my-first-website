from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "FitBuddy"
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'fitbuddy.db').as_posix()}"
    admin_key: str = "change-me-in-production"
    debug: bool = True
    gemini_api_key: str = ""
    gemini_workout_model: str = "gemini-3.8-flash"
    gemini_tip_model: str = "gemini-3.8-flash"
    gemini_temperature: float = 0.7
    gemini_max_output_tokens: int = 5000

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
