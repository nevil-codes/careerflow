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
    "title": "Senior Backend Engineer (m/w/d)",
    "company": "Acme Robotics GmbH",
    "location": "Munich, Germany",
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
    assert body["title"] == "Senior Backend Engineer (m/w/d)"
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
    use_fake(monkeypatch, json.dumps(GOOD | {"title": "senior   backend engineer"}))
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
        "title": "Werkstudent (m/w/d) Data Engineering",
        "company": "Beispiel GmbH",
        "location": "Köln",
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
