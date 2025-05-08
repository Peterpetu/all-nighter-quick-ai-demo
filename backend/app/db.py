from sqlmodel import create_engine, SQLModel, Session
from pathlib import Path

# Store the SQLite DB in the shared volume at /app/data
DATABASE_URL = "sqlite:///./data/tasks.db"
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

def init_db():
    """Create database tables."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Provide a transactional scope around a series of operations."""
    with Session(engine) as session:
        yield session
