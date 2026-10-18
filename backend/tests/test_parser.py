import pytest

from app.models import ItemStatus, ItemType
from app.seed.parser import ContextParseError, parse_candidate_context

MINIMAL_PROFILE = "## Profile\n- name: Test User\n- german_level: A2\n"


def by_title(ctx):
    return {item.title: item for item in ctx.items}


def test_example_file_parses(example_text):
    ctx = parse_candidate_context(example_text)

    assert ctx.profile.full_name == "Alex Example"
    assert ctx.profile.german_level == "B1 (Goethe certificate, B2 in progress)"
    counts = {t: sum(i.type == t for i in ctx.items) for t in ItemType}
    assert counts == {
        ItemType.EDUCATION: 2,
        ItemType.JOB: 1,
        ItemType.PROJECT: 2,
        ItemType.COURSE: 1,
        ItemType.SKILL: 4,
    }
    assert ctx.warnings == []


def test_example_statuses_are_exact(example_text):
    items = by_title(parse_candidate_context(example_text))

    assert items["M.Sc. Data Science"].status is ItemStatus.IN_PROGRESS
    assert items["Software Engineer"].status is ItemStatus.IN_PROGRESS
    assert items["CareerFlow"].status is ItemStatus.IN_PROGRESS
    assert items["B.Tech. Computer Engineering"].status is ItemStatus.COMPLETED
    assert items["Sentiment Classifier"].status is ItemStatus.COMPLETED
    assert items["Python"].status is None


def test_example_fields(example_text):
    items = by_title(parse_candidate_context(example_text))

    job = items["Software Engineer"]
    assert job.organization == "Acme GmbH"
    assert job.stack == ["Python", "FastAPI", "PostgreSQL"]
    assert job.metrics == ["Cut p95 API latency by 40%", "Migrated 3 services to async"]
    assert job.description == "Owned the internal analytics API."
    assert items["Sentiment Classifier"].metrics == ["F1 0.91 on held-out set", "120 GitHub stars"]
    assert items["CareerFlow"].link == "https://github.com/example/careerflow"
    assert "Notes" not in items


@pytest.mark.parametrize("raw", ["in-progress", "In Progress", "IN_PROGRESS", "**in progress**"])
def test_in_progress_spellings_stay_in_progress(raw):
    ctx = parse_candidate_context(MINIMAL_PROFILE + f"## Projects\n### P\n- status: {raw}\n")
    assert ctx.items[0].status is ItemStatus.IN_PROGRESS


def test_description_mentioning_completed_does_not_change_status():
    text = MINIMAL_PROFILE + (
        "## Projects\n### P\n- status: in-progress\n- result: completed phase 1\nAlmost completed.\n"
    )
    item = parse_candidate_context(text).items[0]
    assert item.status is ItemStatus.IN_PROGRESS
    assert item.description == "result: completed phase 1\nAlmost completed."


@pytest.mark.parametrize("raw", ["done", "wip", "ongoing", "finished", "complete"])
def test_unknown_status_is_rejected_not_guessed(raw):
    with pytest.raises(ContextParseError, match="unknown status"):
        parse_candidate_context(MINIMAL_PROFILE + f"## Projects\n### P\n- status: {raw}\n")


@pytest.mark.parametrize("section", ["Education", "Experience", "Projects", "Courses"])
def test_missing_status_is_rejected(section):
    with pytest.raises(ContextParseError, match="has no status"):
        parse_candidate_context(MINIMAL_PROFILE + f"## {section}\n### Thing\n- link: x\n")


def test_german_level_is_verbatim():
    text = "## Profile\n- name: T\n- German Level:  A2.2 (telc, 2025)  \n"
    assert parse_candidate_context(text).profile.german_level == "A2.2 (telc, 2025)"


@pytest.mark.parametrize(
    "profile", ["## Profile\n- name: T\n", "## Profile\n- german_level: A2\n", "## Profile\n- name: T\n- german_level:\n"]
)
def test_required_profile_fields(profile):
    with pytest.raises(ContextParseError, match="missing required field"):
        parse_candidate_context(profile)


def test_duplicate_item_is_rejected():
    text = MINIMAL_PROFILE + "## Projects\n### P\n- status: planned\n### P\n- status: completed\n"
    with pytest.raises(ContextParseError, match="duplicate"):
        parse_candidate_context(text)


def test_duplicate_field_is_rejected():
    text = MINIMAL_PROFILE + "## Projects\n### P\n- status: in-progress\n- status: completed\n"
    with pytest.raises(ContextParseError, match="duplicate field"):
        parse_candidate_context(text)
