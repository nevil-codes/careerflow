import json

import pytest
from sqlmodel import select

from app.api import postings as postings_api
from app.llm.base import ProviderUnavailable
from app.models import Posting, ProviderConfig
from tests.fakes import FakeProvider

JD = """Senior Backend Engineer (m/w/d)
Acme Robotics GmbH · Munich, Germany · Hybrid

We are looking for a backend engineer to build our fleet APIs.
Apply at https://jobs.acme-robotics.example/42
"""

GOOD = {
    "title_original": "Senior Backend Engineer (m/w/d)",
    "title_en": "Senior Backend Engineer (m/w/d)",
    "company": "Acme Robotics GmbH",
    "location_en": "Munich, Germany",
    "language": "english",
    "url": "https://jobs.acme-robotics.example/42",
}


@pytest.fixture
def active_provider(session):
    session.add(ProviderConfig(name="Local", provider="ollama", model="m", enabled=True))
    session.commit()


def use_fake(monkeypatch, *replies):
    fake = FakeProvider(*replies)
    monkeypatch.setattr(postings_api, "get_active_provider", lambda _s: (None, fake))
    return fake


def test_paste_extracts_and_saves(client, session, monkeypatch, active_provider):
    fake = use_fake(monkeypatch, json.dumps(GOOD))

    res = client.post("/postings/from-text", json={"description": JD})

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["title"] == "Senior Backend Engineer"  # gender tag dropped
    assert body["title_original"] is None  # English posting: nothing to keep
    assert body["company"] == "Acme Robotics GmbH"
    assert body["location"] == "Munich, Germany"
    assert body["language"] == "English"
    assert body["url"] == "https://jobs.acme-robotics.example/42"
    assert body["source"] == "pasted"
    assert body["description"] == JD  # verbatim, untouched
    assert JD in fake.calls[0][0][1]["content"]


def test_made_up_company_is_rejected_and_retried(client, monkeypatch, active_provider):
    invented = GOOD | {"company": "Acme Inc."}
    fake = use_fake(monkeypatch, json.dumps(invented), json.dumps(GOOD))

    res = client.post("/postings/from-text", json={"description": JD})

    assert res.status_code == 201
    assert res.json()["company"] == "Acme Robotics GmbH"
    feedback = fake.calls[1][0][-1]["content"]
    assert "'Acme Inc.' does not appear in the posting text" in feedback


def test_made_up_url_is_rejected(client, monkeypatch, active_provider):
    use_fake(monkeypatch, *[json.dumps(GOOD | {"url": "https://acme.example/careers"})] * 3)

    res = client.post("/postings/from-text", json={"description": JD})

    assert res.status_code == 502
    assert "does not appear" in res.json()["detail"]


def test_title_match_ignores_case_and_whitespace(client, monkeypatch, active_provider):
    use_fake(monkeypatch, json.dumps(GOOD | {"title_original": "senior   backend engineer"}))
    assert client.post("/postings/from-text", json={"description": JD}).status_code == 201


def test_failed_extraction_saves_nothing(client, session, monkeypatch, active_provider):
    use_fake(monkeypatch, "nope", "nope", "nope")

    res = client.post("/postings/from-text", json={"description": JD})

    assert res.status_code == 502
    assert "Could not read the posting" in res.json()["detail"]
    assert session.exec(select(Posting)).all() == []


def test_unreachable_provider_is_503(client, monkeypatch, active_provider):
    def down(_messages):
        raise ProviderUnavailable("Cannot reach Ollama")

    use_fake(monkeypatch, down)
    res = client.post("/postings/from-text", json={"description": JD})
    assert res.status_code == 503
    assert res.json()["detail"] == "Cannot reach Ollama"


def test_no_provider_enabled_is_409(client):
    res = client.post("/postings/from-text", json={"description": JD})
    assert res.status_code == 409
    assert "No LLM provider is enabled" in res.json()["detail"]


@pytest.mark.parametrize("text", ["too short", " " * 100])
def test_paste_must_have_substance(client, text):
    assert client.post("/postings/from-text", json={"description": text}).status_code == 422


GERMAN_JD = """Werkstudent (m/w/d) Data Engineering bei der Beispiel GmbH in Köln.
Wir suchen dich für den Aufbau von Pipelines mit Python und SQL. Du arbeitest eng mit
unserem Team zusammen und bist für die Datenqualität zuständig. Bewirb dich bei uns
unter karriere.beispiel.example/jobs/42 und werde Teil von unserem Team."""


def test_scheme_added_to_bare_url_and_language_detected(client, monkeypatch, active_provider):
    reply = {
        "title_original": "Werkstudent (m/w/d) Data Engineering",
        "title_en": "Working Student Data Engineering",
        "company": "Beispiel GmbH",
        "location_en": "Cologne, Germany",
        "language": None,
        "url": "karriere.beispiel.example/jobs/42",
    }
    use_fake(monkeypatch, json.dumps(reply))

    body = client.post("/postings/from-text", json={"description": GERMAN_JD}).json()

    assert body["url"] == "https://karriere.beispiel.example/jobs/42"
    assert body["language"] == "German"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (GERMAN_JD, "German"),
        (JD + " You will work with our team and you are responsible for the APIs of the fleet.", "English"),
        ("Python SQL Docker Kubernetes", None),
    ],
)
def test_detect_language(text, expected):
    from app.llm.extract_posting import detect_language

    assert detect_language(text) == expected


def test_german_posting_is_stored_in_english(client, monkeypatch, active_provider):
    reply = {
        "title_original": "Werkstudent (m/w/d) Data Engineering",
        "title_en": "Working Student Data Engineering",
        "company": "Beispiel GmbH",
        "location_en": "Cologne, Germany",
        "language": "German",
        "url": None,
    }
    use_fake(monkeypatch, json.dumps(reply))

    body = client.post("/postings/from-text", json={"description": GERMAN_JD}).json()

    assert body["title"] == "Working Student Data Engineering"
    assert body["title_original"] == "Werkstudent (m/w/d) Data Engineering"
    assert body["company"] == "Beispiel GmbH"
    assert body["location"] == "Cologne, Germany"
    assert body["description"] == GERMAN_JD
    found = client.get("/postings", params={"q": "werkstudent"}).json()
    assert [p["id"] for p in found] == [body["id"]]


def test_invented_original_title_is_rejected(client, monkeypatch, active_provider):
    bad = {
        "title_original": "Working Student Data Engineering",  # English, not in the German text
        "title_en": "Working Student Data Engineering",
        "company": "Beispiel GmbH",
    }
    fake = use_fake(monkeypatch, json.dumps(bad), json.dumps(bad | {"title_original": "Werkstudent (m/w/d) Data Engineering"}))

    body = client.post("/postings/from-text", json={"description": GERMAN_JD}).json()

    assert body["title_original"] == "Werkstudent (m/w/d) Data Engineering"
    assert "does not appear in the posting text" in fake.calls[1][0][-1]["content"]


@pytest.mark.parametrize("placeholder", [":null", "null", "N/A", " unknown ", '"none"', ""])
def test_placeholder_strings_count_as_missing(placeholder):
    from app.llm.extract_posting import ExtractedPosting

    value = ExtractedPosting.model_validate(
        GOOD | {"location_en": placeholder, "url": placeholder}, context={"source": JD}
    )
    assert value.location_en is None
    assert value.url is None


def test_placeholder_title_gets_required_feedback_not_null_hint(client, monkeypatch, active_provider):
    fake = use_fake(monkeypatch, json.dumps(GOOD | {"title_original": ":null"}), json.dumps(GOOD))

    assert client.post("/postings/from-text", json={"description": JD}).status_code == 201
    feedback = fake.calls[1][0][-1]["content"]
    assert "title_original" in feedback
    assert "use null" not in feedback


@pytest.mark.parametrize(
    ("title_en", "expected"),
    [
        ("Working Student (m/w/d) Data Engineering", "Working Student Data Engineering"),
        ("Backend Engineer (m/f/d)", "Backend Engineer"),
        ("Data Scientist (w/m/d)", "Data Scientist"),
        ("ML Engineer (all genders)", "ML Engineer"),
        ("Product Manager (Payments)", "Product Manager (Payments)"),
    ],
)
def test_gender_tags_removed_from_english_title(title_en, expected):
    from app.llm.extract_posting import ExtractedPosting

    posting = ExtractedPosting(title_original="x", title_en=title_en, company="y")
    assert posting.to_posting_fields()["title"] == expected
