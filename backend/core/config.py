import os
from dotenv import load_dotenv

# Load environment variables from a .env file



load_dotenv()



class Settings:
    supabase_url: str = os.getenv("supabase_url")
    supabase_key: str = os.getenv("supabase_key")
    gen_ai_key: str = os.getenv("gen_ai_key")
    log_level: str = os.getenv("log_level", "INFO").upper() # Log level with default
# Create a single config object that other files can import
config = Settings()
