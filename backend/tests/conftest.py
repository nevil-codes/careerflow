from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.db import get_session, make_engine
from app.main import app

EXAMPLE_FILE = Path(__file__).resolve().parents[2] / "candidate_context.example.md"


@pytest.fixture
def engine():
    # StaticPool: one shared in-memory connection so every session sees the same DB.
    engine = make_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine) -> Iterator[TestClient]:
    def _session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def example_text() -> str:
    return EXAMPLE_FILE.read_text(encoding="utf-8")
