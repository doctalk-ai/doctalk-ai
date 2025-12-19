import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables from a .env file located next to this config module
dotenv_path = Path(__file__).resolve().parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    logger.debug(f"Loaded environment variables from {dotenv_path}")
else:
    # Fall back to the default behavior (cwd .env or system envs)
    load_dotenv()
    logger.debug("No local .env found next to config.py; falling back to default load_dotenv()")


class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    GEN_AI_KEY: str = os.getenv("GEN_AI_KEY")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()  # Log level with default
    LOG_USE_UTC: bool = os.getenv("LOG_USE_UTC", "false").lower() in ("1", "true", "yes")# if env var is set to true-like value you can see it in utc

    # Backwards-compatible lowercase properties for accessing config values
    @property
    def supabase_url(self) -> str:
        return self.SUPABASE_URL

    @property
    def supabase_key(self) -> str:
        return self.SUPABASE_KEY



config = Settings()
