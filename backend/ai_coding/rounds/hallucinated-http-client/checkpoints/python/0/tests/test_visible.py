"""Visible test — passes against a mock. Stands in for BOTH the AI's
invented method AND the real `httpx.get(...).json()` combo so either
implementation passes here. That's exactly why the hidden test is
needed against a real server — the visible test alone cannot catch
the hallucination."""
from unittest.mock import MagicMock, patch

import client


def _mock_response(payload):
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    r.status_code = 200
    return r


def test_fetch_user_returns_dict():
    expected = {"id": "u-1", "name": "Alex"}
    with patch.object(client.httpx, "get", return_value=_mock_response(expected)), \
         patch.object(client.httpx, "get_json", return_value=expected, create=True):
        result = client.fetch_user("u-1")
    assert result == expected
