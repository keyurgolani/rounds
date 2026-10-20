"""Minimal PocketBase REST client for the account-scope harness.

Standard library only (urllib) so the probe image needs no dependency
install and no new dependency enters the repo. Every call returns a
``Response`` carrying the HTTP status and parsed JSON body (or ``None``).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Response:
    status: int
    body: Any
    elapsed_ms: int


class PBClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Response:
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = None
        headers = {"Accept": "application/json"}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                status = resp.status
        except urllib.error.HTTPError as err:
            raw = err.read()
            status = err.code
        elapsed_ms = int((time.monotonic() - start) * 1000)
        parsed: Any = None
        if raw:
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                parsed = None
        return Response(status=status, body=parsed, elapsed_ms=elapsed_ms)

    # -- auth -------------------------------------------------------------
    def wait_healthy(self, attempts: int = 60, delay: float = 1.0) -> None:
        for _ in range(attempts):
            try:
                r = self._request("GET", "/api/health")
                if r.status == 200:
                    return
            except urllib.error.URLError:
                pass
            time.sleep(delay)
        raise RuntimeError(f"PocketBase did not become healthy at {self.base_url}")

    def signup(self, email: str, password: str) -> Response:
        return self._request(
            "POST",
            "/api/collections/users/records",
            json_body={
                "email": email,
                "password": password,
                "passwordConfirm": password,
            },
        )

    def auth_password(self, identity: str, password: str) -> Response:
        return self._request(
            "POST",
            "/api/collections/users/auth-with-password",
            json_body={"identity": identity, "password": password},
        )

    def admin_auth(self, identity: str, password: str) -> Response:
        return self._request(
            "POST",
            "/api/admins/auth-with-password",
            json_body={"identity": identity, "password": password},
        )

    # -- records ----------------------------------------------------------
    def create(self, collection: str, token: str, payload: dict[str, Any]) -> Response:
        return self._request(
            "POST",
            f"/api/collections/{collection}/records",
            token=token,
            json_body=payload,
        )

    def update(self, collection: str, record_id: str, payload: dict, token: str | None = None) -> Response:
        return self._request(
            "PATCH",
            f"/api/collections/{collection}/records/{record_id}",
            token=token,
            json_body=payload,
        )

    def view(self, collection: str, record_id: str, token: str | None = None) -> Response:
        return self._request(
            "GET",
            f"/api/collections/{collection}/records/{record_id}",
            token=token,
        )

    def listing(
        self,
        collection: str,
        token: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> Response:
        p = {"perPage": 200}
        if params:
            p.update(params)
        return self._request(
            "GET",
            f"/api/collections/{collection}/records",
            token=token,
            params=p,
        )

    def delete(self, collection: str, record_id: str, token: str | None = None) -> Response:
        return self._request(
            "DELETE",
            f"/api/collections/{collection}/records/{record_id}",
            token=token,
        )

    def collections_meta(self, admin_token: str) -> Response:
        return self._request(
            "GET", "/api/collections", token=admin_token, params={"perPage": 200}
        )

    # -- other routes -----------------------------------------------------
    def post(self, path: str, body: dict[str, Any], token: str | None = None) -> Response:
        """POST JSON to any route on this base URL (the runner, through nginx)."""
        return self._request("POST", path, token=token, json_body=body)

    def get(self, path: str, token: str | None = None) -> Response:
        """GET any route on this base URL."""
        return self._request("GET", path, token=token)

    def wait_for(self, path: str, ready: "Callable[[Response], bool]", attempts: int = 60, delay: float = 1.0) -> Response:
        """Poll a route until `ready` accepts the answer (connection errors
        count as not ready), or raise."""
        last: Response | None = None
        for _ in range(attempts):
            try:
                last = self._request("GET", path)
                if ready(last):
                    return last
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(delay)
        raise RuntimeError(
            f"{self.base_url}{path} never became ready (last status={last.status if last else 'no answer'})"
        )
