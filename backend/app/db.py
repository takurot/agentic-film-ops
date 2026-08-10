"""SQLite engine/session setup (local-only persistence, Issue #35)."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

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
