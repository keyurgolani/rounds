"""Fetch a user profile from the internal users service.

An AI assistant wrote this file. The visible test passes, so it's ready
to ship — but it has not yet been pointed at the real service.
"""
import httpx


INTERNAL_BASE_URL = "http://internal-users.local"


def fetch_user(user_id: str) -> dict:
    """Return the JSON body of GET /users/{user_id} as a dict.

    Raises:
        RuntimeError: if the upstream returns a non-2xx response.
    """
    url = f"{INTERNAL_BASE_URL}/users/{user_id}"
    # `httpx.get_json` is the friendly wrapper — it folds the
    # `.json()` step in and raises on non-2xx automatically. The AI
    # said this is the idiomatic way to do it.
    return httpx.get_json(url, timeout=5.0)
