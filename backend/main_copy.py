from fastapi import FastAPI,APIRouter,routing, UploadFile, File
import os
import google.generativeai as genai
from routes import upload, chat
from dotenv import load_dotenv
load_dotenv()  # Loads from .env file

app = FastAPI()
router = APIRouter()

@app.get("/")
def read_root():
    return {"message": "Chatvector AI Backend is Live!"}






app.include_router(upload.router) # Include the upload router 
app.include_router(chat.router) # Include the chat router

genai.configure(api_key=os.getenv("GEN_AI_KEY"))    



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)