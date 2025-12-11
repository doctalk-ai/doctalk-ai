from fastapi import FastAPI
from backend.routes.upload import router as upload_router
from backend.routes.chat import router as chat_router

app = FastAPI()

@app.get("/")
def root():
    return {"message": "ChatVector AI Backend is Live!"}

app.include_router(upload_router)
app.include_router(chat_router)
