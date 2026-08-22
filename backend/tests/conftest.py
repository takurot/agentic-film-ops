import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

# Runtime profile selection is explicit in production. The test suite uses the
# deterministic replay profile unless an individual test opts into LIVE_GEMINI.
os.environ.setdefault("FILMOPS_RUNTIME_MODE", "RECORDED_REPLAY")


@pytest.fixture
def session():
    """A fresh in-memory SQLite session, isolated per test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()
