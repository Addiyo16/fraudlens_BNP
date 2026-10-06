
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker


# Project structure:
# fraudlens/
#   backend/
#     app/
#       database.py
#     fraudlens.db

BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BACKEND_DIR / "fraudlens.db"

DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    """Provide a database session to FastAPI endpoints."""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create database tables that do not already exist."""
    # Import models so SQLAlchemy registers every table.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
