"""SQLite engine/session setup (local-only persistence, Issue #35)."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Importing for its side effect: registering Incident/Analysis on Base's
# metadata, so init_db() creates their tables even if nothing else has
# imported app.workflow yet (e.g. a bare `python -c "from app.db import
# init_db; init_db()"`).
import app.workflow  # noqa: F401
from app.models import Base

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DATA_DIR / "agentic_filmops.db"


def create_db_engine(db_path: Path = DEFAULT_DB_PATH) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


engine = create_db_engine()


def init_db(bind: Engine | None = None) -> None:
    Base.metadata.create_all(bind or engine)


def get_session(bind: Engine | None = None) -> Session:
    return sessionmaker(bind=bind or engine)()


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""
    db = get_session()
    try:
        yield db
    finally:
        db.close()
