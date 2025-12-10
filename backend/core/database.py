import os
from dotenv import load_dotenv
from supabase import create_client, Client  # <-- Make sure this is imported



load_dotenv()  # Loads from .env file

# supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


def test_db():
    try:
        response = supabase.table('documents').select("*").limit(1).execute()
        return {"status": "Database connected!", "data": response.data}
    except Exception as e:
        return {"error": str(e)}