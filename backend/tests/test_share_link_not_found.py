"""A share token that leads nowhere gets the existing not-found (ROUNDS-00B-L02).

The relation quarantine moves a share link whose resume or variant belongs to
another account, so its token then matches no link. A legacy link with neither
target, or one whose variant or resume is gone, must answer exactly like that
missing token (the same status and body, never a 500), and record no view.

Since ROUNDS-00B-L03 stage 1 no public read records a view at all, and a
resolved link answers only its projection (backend/tests/test_share_public_read.py).
"""
from unittest.mock import patch

import pytest

LINK_OWNER = "owner-of-the-link"
# A well-formed token, so each read reaches the link lookup.
TOKEN = "AbCdEfGhIjKlMnOpQrStUv"


def _comparable(res):
    """Status and body, minus the per-request correlation id."""
    body = res.json()
    if isinstance(body, dict):
        body = {k: v for k, v in body.items() if k != "correlation_id"}
    return res.status_code, body


def _read(client, link, records):
    views = []

    async def fake_admin_get(path, params=None):
        if "resume_share_links" in path:
            return {"items": [link] if link else []}
        for prefix, record in records.items():
            if prefix in path:
                return record
        return None

    async def fake_admin_post(path, body):
        views.append(path)
        return {"id": "v1"}

    with patch("routers.share.pb_admin_get", fake_admin_get), \
         patch("app.pb_auth.pb_admin_post", fake_admin_post):
        res = client.get(f"/api/share/by-token/{TOKEN}")
    return res, views


@pytest.fixture
def missing_token(client):
    res, views = _read(client, None, {})
    assert res.status_code == 404
    assert not views
    return _comparable(res)


@pytest.mark.parametrize(
    "link, records",
    [
        # A link with no target at all.
        ({"id": "l1", "user": LINK_OWNER, "resume": "", "variant": "", "token": TOKEN}, {}),
        # A link whose variant is gone.
        ({"id": "l1", "user": LINK_OWNER, "resume": "", "variant": "v1", "token": TOKEN}, {"resume_variants": None}),
        # A link whose resume is gone.
        ({"id": "l1", "user": LINK_OWNER, "resume": "r1", "variant": "", "token": TOKEN}, {"resumes": None}),
    ],
    ids=["no-target", "variant-gone", "resume-gone"],
)
def test_a_link_that_leads_nowhere_answers_like_a_missing_token(client, missing_token, link, records):
    res, views = _read(client, link, records)
    assert _comparable(res) == missing_token
    assert not views, "no view is recorded for a link that leads nowhere"


def test_a_link_with_a_target_still_resolves(client):
    link = {"id": "l1", "user": LINK_OWNER, "resume": "r1", "variant": "", "token": TOKEN}
    record = {"id": "r1", "data": {}, "template_id": "modern", "design": {}, "name": "R"}
    res, views = _read(client, link, {"resumes": record})
    assert res.status_code == 200
    assert set(res.json()) == {"data", "template_id", "design"}
    assert not views, "a public read records no view"
