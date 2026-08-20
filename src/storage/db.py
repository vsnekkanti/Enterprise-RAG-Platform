from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from .models import Base

DATABASE_URL = "postgresql+psycopg://raguser:ragpass@localhost:5432/rag_db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    return SessionLocal()
