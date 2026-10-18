from pathlib import Path

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from app.models import ItemStatus, LockedFieldError, Profile, ProfileItem
from app.seed import __main__ as cli
from app.seed.parser import parse_candidate_context
from app.seed.seed import SeedIntegrityError, seed_profile, verify_seed


def items_by_title(session: Session) -> dict[str, ProfileItem]:
    return {i.title: i for i in session.exec(select(ProfileItem))}


def test_seed_imports_profile_and_items(session, example_text):
    ctx = parse_candidate_context(example_text)
    result = seed_profile(session, ctx)

    assert (result.created, result.updated, result.deleted) == (len(ctx.items), 0, 0)
    profile = session.exec(select(Profile)).one()
    assert profile.german_level == "B1 (Goethe certificate, B2 in progress)"
    assert len(items_by_title(session)) == len(ctx.items)


def test_seed_preserves_every_status_exactly(session, example_text):
    ctx = parse_candidate_context(example_text)
    seed_profile(session, ctx)

    stored = items_by_title(session)
    for parsed in ctx.items:
        assert stored[parsed.title].status == parsed.status
    in_progress = [t for t, i in stored.items() if i.status is ItemStatus.IN_PROGRESS]
    assert sorted(in_progress) == ["CareerFlow", "M.Sc. Data Science", "Software Engineer"]


def test_reseed_is_idempotent_and_keeps_ids(session, example_text):
    ctx = parse_candidate_context(example_text)
    seed_profile(session, ctx)
    ids = {t: i.id for t, i in items_by_title(session).items()}

    result = seed_profile(session, parse_candidate_context(example_text))

    assert (result.created, result.updated, result.deleted) == (0, 0, 0)
    assert {t: i.id for t, i in items_by_title(session).items()} == ids


def test_reseed_applies_file_changes(session, example_text):
    seed_profile(session, parse_candidate_context(example_text))
    edited = (
        example_text.replace("- german_level: B1 (Goethe certificate, B2 in progress)", "- german_level: B2")
        .replace("### Sentiment Classifier\n- status: completed", "### Sentiment Classifier\n- status: paused")
        .replace("- Docker\n", "")
    )

    result = seed_profile(session, parse_candidate_context(edited))

    assert (result.updated, result.deleted) == (1, 1)
    items = items_by_title(session)
    assert items["Sentiment Classifier"].status is ItemStatus.PAUSED
    assert "Docker" not in items
    assert session.exec(select(Profile)).one().german_level == "B2"


def test_file_is_the_only_way_to_complete_an_in_progress_item(session, example_text):
    seed_profile(session, parse_candidate_context(example_text))
    item = items_by_title(session)["CareerFlow"]

    item.status = ItemStatus.COMPLETED
    with pytest.raises(LockedFieldError):
        session.commit()
    session.rollback()

    finished = example_text.replace(
        "### CareerFlow\n- status: in-progress", "### CareerFlow\n- status: completed"
    )
    seed_profile(session, parse_candidate_context(finished))
    assert items_by_title(session)["CareerFlow"].status is ItemStatus.COMPLETED


def test_german_level_is_locked_outside_seed(session, example_text):
    seed_profile(session, parse_candidate_context(example_text))
    profile = session.exec(select(Profile)).one()

    profile.german_level = "C1"
    with pytest.raises(LockedFieldError):
        session.commit()
    session.rollback()
    assert session.exec(select(Profile)).one().german_level == "B1 (Goethe certificate, B2 in progress)"


def test_verify_detects_status_drift(session, example_text):
    ctx = parse_candidate_context(example_text)
    seed_profile(session, ctx)
    # Bypass the ORM guard to simulate corruption by some other writer.
    session.execute(text("UPDATE profile_item SET status = 'completed' WHERE title = 'CareerFlow'"))
    session.commit()

    with pytest.raises(SeedIntegrityError, match="CareerFlow"):
        verify_seed(session, ctx)


def test_cli_seeds_from_file(engine, monkeypatch, tmp_path: Path, example_text, capsys):
    monkeypatch.setattr(cli, "engine", engine)
    path = tmp_path / "candidate_context.md"
    path.write_text(example_text)

    assert cli.main([str(path)]) == 0
    assert "German level: B1 (Goethe certificate, B2 in progress)" in capsys.readouterr().out


def test_cli_reports_parse_errors(engine, monkeypatch, tmp_path: Path, capsys):
    monkeypatch.setattr(cli, "engine", engine)
    path = tmp_path / "candidate_context.md"
    path.write_text("## Profile\n- name: T\n- german_level: A1\n## Projects\n### P\n- status: wip\n")

    assert cli.main([str(path)]) == 1
    assert "unknown status 'wip'" in capsys.readouterr().err
    with Session(engine) as s:
        assert s.exec(select(Profile)).first() is None


def test_cli_missing_file(engine, monkeypatch, tmp_path: Path, capsys):
    monkeypatch.setattr(cli, "engine", engine)
    assert cli.main([str(tmp_path / "nope.md")]) == 1
    assert "not found" in capsys.readouterr().err
