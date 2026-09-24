from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SPA Inventory & Procurement API"
    app_version: str = "1.0.0"
    database_url: str = "postgresql+psycopg://spa:spa@db:5432/spa"
    expiry_alert_days: int = 30
    no_movement_days: int = 90

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
