from supabase import create_client
from backend.core.config import config
from backend.core.logging_config import setup_logging
import logging

logger = logging.getLogger(__name__)

supabase_client = create_client(
    config.supabase_url,
    config.supabase_key
)
logging.info("Supabase client initialized successfully.")