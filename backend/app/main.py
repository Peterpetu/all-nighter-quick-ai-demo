# library imports
from fastapi import FastAPI
from dotenv import load_dotenv

# local imports
from app.db import init_db
from app.routers.tasks import router as tasks_router
from app.routers.chat import router as chat_router

load_dotenv

app = FastAPI(title="AI-Powered Todo App")

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(tasks_router)
app.include_router(chat_router)

@app.get("/health")
def health():
    return {"status": "ok"}