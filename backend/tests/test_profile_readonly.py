import pytest
from sqlmodel import select

from app.llm.context import PROFILE_RULES, profile_context
from app.llm.registry import NoProviderEnabled, get_active_provider
from app.models import ItemType, LockedFieldError, Profile, ProfileItem
from app.seed.parser import parse_candidate_context
from app.seed.seed import seed_profile


@pytest.fixture
def seeded(session, example_text):
    seed_profile(session, parse_candidate_context(example_text))
    return session


def test_cannot_add_profile_items_outside_seed(seeded):
    profile = seeded.exec(select(Profile)).one()
    seeded.add(ProfileItem(profile_id=profile.id, type=ItemType.SKILL, title="Kubernetes"))
    with pytest.raises(LockedFieldError, match="read-only"):
        seeded.commit()


def test_cannot_edit_profile_items_outside_seed(seeded):
    item = seeded.exec(select(ProfileItem).where(ProfileItem.title == "CareerFlow")).one()
    item.metrics = ["10k users"]
    with pytest.raises(LockedFieldError, match="read-only"):
        seeded.commit()


def test_cannot_delete_profile_items_outside_seed(seeded):
    seeded.delete(seeded.exec(select(ProfileItem)).first())
    with pytest.raises(LockedFieldError, match="read-only"):
        seeded.commit()


def test_cannot_edit_profile_outside_seed(seeded):
    seeded.exec(select(Profile)).one().headline = "Staff Engineer"
    with pytest.raises(LockedFieldError, match="read-only"):
        seeded.commit()


def test_reading_and_noop_assignment_is_fine(seeded):
    item = seeded.exec(select(ProfileItem).where(ProfileItem.title == "CareerFlow")).one()
    item.title = item.title  # same value: not a modification
    seeded.commit()


def test_profile_context_carries_statuses_and_german_verbatim(seeded):
    text = profile_context(seeded)

    assert "German level: B1 (Goethe certificate, B2 in progress)" in text
    assert "- CareerFlow [status: in-progress]" in text
    assert "- M.Sc. Data Science [status: in-progress]" in text
    assert "- Sentiment Classifier [status: completed]" in text
    assert "Result: Cut p95 API latency by 40%" in text
    assert "Python, TypeScript, SQL, Docker" in text
    assert "Never describe an in-progress" in PROFILE_RULES


def test_profile_context_none_before_seed(session):
    assert profile_context(session) is None


def test_no_active_provider(session):
    with pytest.raises(NoProviderEnabled):
        get_active_provider(session)
