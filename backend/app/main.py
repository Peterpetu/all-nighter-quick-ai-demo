from fastapi import FastAPI
from app.db import init_db
from app.routers.tasks import router as tasks_router

app = FastAPI(title="AI-Powered Todo App")

@app.on_event("startup")
def on_startup():
    init_db()

app.include_router(tasks_router)

@app.get("/health")
def health():
    return {"status": "ok"}