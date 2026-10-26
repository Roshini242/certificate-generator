from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite stores everything in one file called certificates.db
DATABASE_URL = "sqlite:///./certificates.db"

# The engine is the actual connection to the database.
# check_same_thread=False is needed for SQLite when used with FastAPI.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# A session is a "conversation" with the database (read/write data).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All our table classes will inherit from this Base.
Base = declarative_base()


def get_db():
    """Gives each API request its own database session, then closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()