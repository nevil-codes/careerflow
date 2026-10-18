from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from app.config import DATABASE_URL


def make_engine(url: str, **kwargs) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, **kwargs)
    if url.startswith("sqlite"):
        # SQLite ignores foreign keys unless enabled per connection.
        @event.listens_for(engine, "connect")
        def _enable_fks(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(DATABASE_URL)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
