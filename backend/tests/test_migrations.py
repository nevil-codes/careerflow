from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlmodel import SQLModel

from app.db import make_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config(url: str) -> Config:
    cfg = Config(BACKEND_DIR / "alembic.ini")
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    return cfg


def test_migrations_match_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    cfg = alembic_config(url)

    command.upgrade(cfg, "head")
    command.check(cfg)  # raises if models have changes not captured in a migration

    tables = set(inspect(make_engine(url)).get_table_names())
    assert set(SQLModel.metadata.tables) <= tables

    command.downgrade(cfg, "base")
    assert set(inspect(make_engine(url)).get_table_names()) == {"alembic_version"}
