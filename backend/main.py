from fastapi import FastAPI, APIRouter # Import APIRouter
import os # Import os for environment variables
import google.generativeai as genai # Import Google Generative AI SDK
from routes import upload, chat # Import the routers
from dotenv import load_dotenv # <-- Import load_dotenv

load_dotenv()  # Loads from .env file

app = FastAPI() # Create FastAPI app instance
router = APIRouter() # Create a router instance

@app.get("/") # Define root endpoint
def read_root():
    return {"message": "Chatvector AI Backend is Live!"}

genai.configure(api_key=os.getenv("GEN_AI_KEY")) # Configure Google Generative AI with API key

app.include_router(upload.router) # Include the upload router 
app.include_router(chat.router) # Include the chat router 

if __name__ == "__main__": # Run the app with Uvicorn
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)