"""CLI: ``python -m app.seed [path/to/candidate_context.md]``."""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import inspect
from sqlmodel import Session

from app.config import BACKEND_DIR
from app.db import engine
from app.seed.parser import ContextParseError, load_candidate_context
from app.seed.seed import SeedIntegrityError, seed_profile

DEFAULT_PATH = Path(
    os.environ.get("CAREERFLOW_CONTEXT_FILE", BACKEND_DIR.parent / "candidate_context.md")
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import the profile from candidate_context.md")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args(argv)

    if not inspect(engine).has_table("profile"):
        print("Database not migrated. Run `uv run alembic upgrade head` first.", file=sys.stderr)
        return 1
    try:
        ctx = load_candidate_context(args.path)
        with Session(engine) as session:
            result = seed_profile(session, ctx)
    except (ContextParseError, SeedIntegrityError) as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1

    for warning in ctx.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    by_status: dict[str, int] = {}
    for item in ctx.items:
        if item.status:
            by_status[item.status.value] = by_status.get(item.status.value, 0) + 1
    print(
        f"Seeded profile {result.profile_id} from {args.path}: "
        f"{result.created} created, {result.updated} updated, {result.deleted} removed. "
        f"German level: {ctx.profile.german_level}. Statuses: {by_status}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
