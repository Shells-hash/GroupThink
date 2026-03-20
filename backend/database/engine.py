from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config import get_settings
from backend.database.base import Base

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables. Called once on app startup."""
    import backend.models  # noqa: F401 — ensures all models are registered on Base
    Base.metadata.create_all(bind=engine)
