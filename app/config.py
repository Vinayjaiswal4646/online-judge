from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./judge.db"
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    sandbox_backend: str = "docker"  # "docker" (safe) or "local" (dev only, NOT safe)
    sandbox_image: str = "python:3.12-slim"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
