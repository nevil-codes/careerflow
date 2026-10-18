from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models import Application, ApplicationEvent, ApplicationStatus, Task

JD = "We are hiring a backend engineer.\n\nRequirements:\n- Python\n- German B2\n"


def make_posting(client, **overrides):
    body = {"title": "Backend Engineer", "company": "Acme", "description": JD} | overrides
    res = client.post("/postings", json=body)
    assert res.status_code == 201, res.text
    return res.json()


def make_application(client, posting_id, **overrides):
    res = client.post("/applications", json={"posting_id": posting_id} | overrides)
    assert res.status_code == 201, res.text
    return res.json()


# --- Postings ---------------------------------------------------------------


def test_create_posting_keeps_pasted_text_verbatim(client):
    posting = make_posting(client, title="  Backend Engineer ", url="https://acme.example/jobs/1")

    assert posting["title"] == "Backend Engineer"
    assert posting["description"] == JD
    assert posting["application_id"] is None
    assert client.get(f"/postings/{posting['id']}").json() == posting


@pytest.mark.parametrize(
    "body",
    [
        {"company": "Acme"},
        {"title": "   ", "company": "Acme"},
        {"title": "X", "company": ""},
        {"title": "X", "company": "Acme", "url": "acme.example/jobs"},
    ],
)
def test_create_posting_validation(client, body):
    assert client.post("/postings", json=body).status_code == 422


def test_list_postings_newest_first_and_search(client):
    make_posting(client, title="Data Engineer", company="Beta")
    make_posting(client, title="ML Engineer", company="Gamma")

    titles = [p["title"] for p in client.get("/postings").json()]
    assert titles == ["ML Engineer", "Data Engineer"]
    assert [p["company"] for p in client.get("/postings", params={"q": "gam"}).json()] == ["Gamma"]


def test_update_posting(client):
    posting = make_posting(client)

    res = client.patch(f"/postings/{posting['id']}", json={"location": "Berlin", "url": ""})

    assert res.status_code == 200
    body = res.json()
    assert body["location"] == "Berlin"
    assert body["url"] is None
    assert body["title"] == "Backend Engineer"
    assert body["updated_at"] >= posting["updated_at"]


@pytest.mark.parametrize("field", ["title", "company"])
def test_update_posting_cannot_blank_required_fields(client, field):
    posting = make_posting(client)
    assert client.patch(f"/postings/{posting['id']}", json={field: " "}).status_code == 422
    assert client.patch(f"/postings/{posting['id']}", json={field: None}).status_code == 422


def test_missing_posting_is_404(client):
    assert client.get("/postings/999").status_code == 404
    assert client.patch("/postings/999", json={"title": "x"}).status_code == 404
    assert client.delete("/postings/999").status_code == 404


def test_delete_posting_cascades(client, session):
    posting = make_posting(client)
    app = make_application(client, posting["id"])
    client.post("/tasks", json={"title": "Follow up", "application_id": app["id"]})

    assert client.delete(f"/postings/{posting['id']}").status_code == 204

    assert session.exec(select(Application)).all() == []
    assert session.exec(select(ApplicationEvent)).all() == []
    assert session.exec(select(Task)).all() == []


# --- Applications -------------------------------------------------------------


def test_create_application_records_initial_event(client):
    posting = make_posting(client)

    app = make_application(client, posting["id"])

    assert app["status"] == "draft"
    assert app["applied_at"] is None
    assert app["posting"] == {"id": posting["id"], "title": "Backend Engineer", "company": "Acme"}
    assert [(e["from_status"], e["to_status"]) for e in app["events"]] == [(None, "draft")]
    assert client.get(f"/postings/{posting['id']}").json()["application_status"] == "draft"


def test_one_application_per_posting(client):
    posting = make_posting(client)
    make_application(client, posting["id"])
    assert client.post("/applications", json={"posting_id": posting["id"]}).status_code == 409


def test_application_for_missing_posting_is_404(client):
    assert client.post("/applications", json={"posting_id": 42}).status_code == 404


def test_status_changes_are_all_recorded(client):
    app = make_application(client, make_posting(client)["id"])

    for status in ["applied", "interviewing", "rejected", "interviewing"]:
        res = client.patch(f"/applications/{app['id']}", json={"status": status})
        assert res.status_code == 200

    body = res.json()
    assert body["status"] == "interviewing"
    assert [(e["from_status"], e["to_status"]) for e in body["events"]] == [
        (None, "draft"),
        ("draft", "applied"),
        ("applied", "interviewing"),
        ("interviewing", "rejected"),
        ("rejected", "interviewing"),
    ]


def test_same_status_or_notes_only_adds_no_event(client):
    app = make_application(client, make_posting(client)["id"])

    client.patch(f"/applications/{app['id']}", json={"status": "draft"})
    body = client.patch(f"/applications/{app['id']}", json={"notes": "Referred by Sam"}).json()

    assert body["notes"] == "Referred by Sam"
    assert len(body["events"]) == 1


def test_applied_at_set_once_on_leaving_draft(client):
    app = make_application(client, make_posting(client)["id"])

    first = client.patch(f"/applications/{app['id']}", json={"status": "applied"}).json()["applied_at"]
    later = client.patch(f"/applications/{app['id']}", json={"status": "interviewing"}).json()

    assert first is not None
    assert later["applied_at"] == first


def test_applied_at_can_be_backdated(client):
    app = make_application(
        client, make_posting(client)["id"], status="applied", applied_at="2026-09-01T09:00:00Z"
    )
    assert app["applied_at"].startswith("2026-09-01T09:00:00")
    assert [(e["from_status"], e["to_status"]) for e in app["events"]] == [(None, "applied")]


def test_status_cannot_be_nulled_or_invalid(client):
    app = make_application(client, make_posting(client)["id"])
    assert client.patch(f"/applications/{app['id']}", json={"status": None}).status_code == 422
    assert client.patch(f"/applications/{app['id']}", json={"status": "ghosted"}).status_code == 422


def test_history_recorded_even_outside_the_api(session, client):
    """The flush hook, not the route, writes history, so direct ORM writes are covered too."""
    app_id = make_application(client, make_posting(client)["id"])["id"]
    app = session.get(Application, app_id)

    app.status = ApplicationStatus.OFFER
    session.commit()

    events = session.exec(select(ApplicationEvent).where(ApplicationEvent.application_id == app_id)).all()
    assert [(e.from_status, e.to_status) for e in events] == [
        (None, ApplicationStatus.DRAFT),
        (ApplicationStatus.DRAFT, ApplicationStatus.OFFER),
    ]


def test_list_applications_filter_and_open_tasks(client):
    a = make_application(client, make_posting(client, title="A")["id"])
    b = make_application(client, make_posting(client, title="B")["id"], status="applied")
    client.post("/tasks", json={"title": "Prep", "application_id": b["id"]})
    done = client.post("/tasks", json={"title": "Send CV", "application_id": b["id"]}).json()
    client.patch(f"/tasks/{done['id']}", json={"status": "done"})

    applied = client.get("/applications", params={"status": "applied"}).json()

    assert [x["id"] for x in applied] == [b["id"]]
    assert applied[0]["open_tasks"] == 1
    assert {x["id"] for x in client.get("/applications").json()} == {a["id"], b["id"]}


def test_delete_application_keeps_posting(client):
    posting = make_posting(client)
    app = make_application(client, posting["id"])

    assert client.delete(f"/applications/{app['id']}").status_code == 204
    assert client.get(f"/postings/{posting['id']}").json()["application_id"] is None
    # A fresh application can be started again.
    make_application(client, posting["id"])


# --- Tasks --------------------------------------------------------------------


def test_task_crud_and_ordering(client):
    app = make_application(client, make_posting(client)["id"])
    later = client.post("/tasks", json={"title": "Later", "due_at": "2026-11-10T00:00:00Z"}).json()
    undated = client.post("/tasks", json={"title": "Someday"}).json()
    soon = client.post(
        "/tasks", json={"title": "Follow up", "due_at": "2026-10-20T00:00:00Z", "application_id": app["id"]}
    ).json()

    assert [t["id"] for t in client.get("/tasks").json()] == [soon["id"], later["id"], undated["id"]]
    assert [t["id"] for t in client.get("/tasks", params={"application_id": app["id"]}).json()] == [soon["id"]]

    client.patch(f"/tasks/{soon['id']}", json={"status": "done"})
    assert soon["id"] not in [t["id"] for t in client.get("/tasks", params={"open": True}).json()]
    assert client.get(f"/applications/{app['id']}").json()["tasks"][0]["status"] == "done"

    assert client.delete(f"/tasks/{later['id']}").status_code == 204
    assert client.delete(f"/tasks/{later['id']}").status_code == 404


@pytest.mark.parametrize(
    "body",
    [{"title": " "}, {"title": "x", "status": "blocked"}, {"title": "x", "application_id": 999}],
)
def test_task_validation(client, body):
    assert client.post("/tasks", json=body).status_code in (404, 422)


def test_task_update_cannot_blank_title_or_status(client):
    task = client.post("/tasks", json={"title": "x"}).json()
    assert client.patch(f"/tasks/{task['id']}", json={"title": ""}).status_code == 422
    assert client.patch(f"/tasks/{task['id']}", json={"status": None}).status_code == 422


def test_datetimes_round_trip_as_utc(client):
    task = client.post("/tasks", json={"title": "x", "due_at": "2026-10-20T12:00:00+02:00"}).json()
    assert datetime.fromisoformat(task["due_at"]) == datetime(2026, 10, 20, 10, tzinfo=UTC)
