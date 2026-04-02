from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Auth
    api_token: str

    # Anthropic
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"

    # CalDAV
    caldav_url: str
    caldav_username: str
    caldav_password: str

    # Nextcloud Deck
    nextcloud_url: str
    nextcloud_username: str
    nextcloud_password: str

    # Task routing
    default_task_list: str = "Inbox"


settings = Settings()  # type: ignore[call-arg]
