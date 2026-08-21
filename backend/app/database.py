# Sets up the connection to the Supabase Postgres database. Every other file
# that needs to read/write the database goes through `get_db()` below.

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

# The actual connection pool to Postgres. `pool_pre_ping` checks a connection
# is still alive before using it, so the app recovers gracefully if Supabase
# drops an idle connection.
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Parent class every database table model (in models.py) inherits from."""

    pass


def get_db():
    """FastAPI dependency: hands each incoming request its own database
    session and guarantees it's closed afterwards, even if the request fails."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
