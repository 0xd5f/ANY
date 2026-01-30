from pydantic_settings import BaseSettings
import os
from pathlib import Path
from dotenv import dotenv_values

class Configs(BaseSettings):
    PORT: int
    DOMAIN: str
    DEBUG: bool
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    API_TOKEN: str
    EXPIRATION_MINUTES: int
    SELF_SIGNED: bool = False
    ROOT_PATH: str = ""
    DECOY_PATH: str | None = None
    CUSTOM_CERT: str | None = None
    CUSTOM_KEY: str | None = None
    
    TELEGRAM_AUTH_ENABLED: bool = False
    
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_ADMIN_IDS: str | None = None

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


CONFIGS = Configs()

try:
    current_file = Path(__file__).resolve()
    telegram_env_path = current_file.parent.parent.parent / "telegrambot" / ".env"
    
    if telegram_env_path.exists():
        tg_config = dotenv_values(telegram_env_path)
        CONFIGS.TELEGRAM_BOT_TOKEN = tg_config.get("API_TOKEN")
        CONFIGS.TELEGRAM_ADMIN_IDS = tg_config.get("ADMIN_USER_IDS")
except Exception as e:
    print(f"Failed to load Telegram config: {e}")

