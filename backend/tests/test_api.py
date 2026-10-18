from app.seed.parser import parse_candidate_context
from app.seed.seed import seed_profile


def test_profile_404_before_seed(client):
    assert client.get("/profile").status_code == 404
    assert client.get("/profile/items").status_code == 404


def test_get_profile(client, session, example_text):
    seed_profile(session, parse_candidate_context(example_text))

    res = client.get("/profile")

    assert res.status_code == 200
    body = res.json()
    assert body["full_name"] == "Alex Example"
    assert body["german_level"] == "B1 (Goethe certificate, B2 in progress)"
    assert set(body) == {"id", "full_name", "headline", "email", "location", "german_level"}


def test_list_items_preserves_status(client, session, example_text):
    ctx = parse_candidate_context(example_text)
    seed_profile(session, ctx)

    res = client.get("/profile/items")

    assert res.status_code == 200
    statuses = {i["title"]: i["status"] for i in res.json()}
    assert statuses == {i.title: (i.status.value if i.status else None) for i in ctx.items}
    assert statuses["CareerFlow"] == "in-progress"


def test_list_items_filter_and_order(client, session, example_text):
    seed_profile(session, parse_candidate_context(example_text))

    res = client.get("/profile/items", params={"type": "education"})

    assert res.status_code == 200
    assert [i["title"] for i in res.json()] == ["M.Sc. Data Science", "B.Tech. Computer Engineering"]


def test_list_items_rejects_unknown_type(client, session, example_text):
    seed_profile(session, parse_candidate_context(example_text))
    assert client.get("/profile/items", params={"type": "hobby"}).status_code == 422
