from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# The path to your SQLite database file
DATABASE_URL = "sqlite:///./data/fitness.db"

# The engine is the connection to the database
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Each model (table) will inherit from this Base class
Base = declarative_base()

# A session is how we read and write to the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    This function hands out database sessions to routers.
    It automatically closes the session when done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    This creates all tables in the database if they don't exist yet.
    Called once when the app starts.
    """
    from models import activity, trail, plan, goal
    Base.metadata.create_all(bind=engine)