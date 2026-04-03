"""Server configuration via pydantic-settings (reads from .env / .env.local)."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Firecrawl — self-hosted JS-rendered scraping for automotive forums, TSBs, recalls
    firecrawl_api_url: str = Field(
        default="http://localhost:3002",
        description="Base URL for the local Firecrawl REST API service.",
    )


settings = Settings()
