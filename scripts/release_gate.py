#!/usr/bin/env python3
"""Decides what a push may publish (ROUNDS-00A-L01 stage 5).

The image workflow runs this before it builds anything:

- A push to main publishes the edge channel: ``edge`` and ``sha-<short>``.
- A ``vX.Y.Z`` or ``vX.Y.Z-PRERELEASE`` tag publishes a release, but only
  once the ``CI`` workflow passed on a push of the exact tagged commit to
  main. It waits while that run is still going and fails closed when no
  run passed, none ran, or the lookup failed. ``latest`` moves only for a
  stable version that no other stable tag outranks.
- Anything else publishes nothing. A deleted ref isn't an error; it just
  publishes nothing.

It writes ``channel`` (edge, release, or none) and ``latest`` (true or
false) to ``$GITHUB_OUTPUT``. It reads GITHUB_EVENT_NAME, GITHUB_EVENT_PATH,
GITHUB_REF, GITHUB_SHA, GITHUB_REPOSITORY, GITHUB_API_URL, and GH_TOKEN.

exit status: 0 decided, 1 nothing may publish
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

CI_WORKFLOW = "ci.yml"
BRANCH = "main"
TAG_PREFIX = "refs/tags/"
RELEASE_TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?")
WAIT_S = 40 * 60  # how long CI on the tagged commit may still be running
APPEAR_S = 5 * 60  # how long a CI run may take to show up at all
POLL_S = 30
MAX_PAGES = 20

# api(path, params) returns the decoded JSON of each page.
Api = Callable[[str, "dict[str, str]"], "list[Any]"]


class GateError(Exception):
    """Nothing may publish; exit status 1."""


def release_version(tag: str) -> tuple[tuple[int, int, int], bool] | None:
    """The tag's (major, minor, patch) and whether it is stable, or None
    when it isn't a release tag."""
    match = RELEASE_TAG.fullmatch(tag)
    if match is None:
        return None
    return (int(match[1]), int(match[2]), int(match[3])), match[4] is None


def moves_latest(tag: str, tags: list[str]) -> bool:
    """Whether ``tag`` is a stable version that no other stable tag outranks."""
    mine = release_version(tag)
    if mine is None or not mine[1]:
        return False
    stable = [v[0] for v in map(release_version, tags) if v is not None and v[1]]
    return all(mine[0] >= other for other in stable)


def _repo_of(run: dict) -> str | None:
    head = run.get("head_repository")
    return head.get("full_name") if isinstance(head, dict) else None


def ci_state(runs: list[dict], sha: str, repo: str) -> str:
    """passed, running, failed, or missing, for CI's runs on pushes of
    ``sha`` to main in ``repo``."""
    mine = [
        run
        for run in runs
        if run.get("head_sha") == sha
        and run.get("event") == "push"
        and run.get("head_branch") == BRANCH
        and _repo_of(run) == repo
    ]
    if any(run.get("status") == "completed" and run.get("conclusion") == "success" for run in mine):
        return "passed"
    if any(run.get("status") != "completed" for run in mine):
        return "running"
    return "failed" if mine else "missing"


def ci_runs(api: Api, repo: str, sha: str) -> list[dict]:
    pages = api(
        f"repos/{repo}/actions/workflows/{CI_WORKFLOW}/runs",
        {"head_sha": sha, "event": "push", "branch": BRANCH, "per_page": "100"},
    )
    runs: list[dict] = []
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("workflow_runs"), list):
            raise GateError("the CI run lookup answered in an unexpected shape, so nothing was published")
        runs.extend(run for run in page["workflow_runs"] if isinstance(run, dict))
    return runs


def release_tags(api: Api, repo: str) -> list[str]:
    tags: list[str] = []
    for page in api(f"repos/{repo}/git/matching-refs/tags/v", {"per_page": "100"}):
        if not isinstance(page, list):
            raise GateError("the tag lookup answered in an unexpected shape, so nothing was published")
        for ref in page:
            name = ref.get("ref") if isinstance(ref, dict) else None
            if isinstance(name, str) and name.startswith(TAG_PREFIX):
                tags.append(name[len(TAG_PREFIX):])
    return tags


def wait_for_ci(
    runs: Callable[[], list[dict]],
    sha: str,
    repo: str,
    *,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    wait_s: float = WAIT_S,
    appear_s: float = APPEAR_S,
    poll_s: float = POLL_S,
) -> None:
    """Returns once CI passed on a push of ``sha`` to main. Raises
    GateError when it failed, never ran, or is still running at the
    deadline."""
    start = clock()
    while True:
        state = ci_state(runs(), sha, repo)
        waited = clock() - start
        if state == "passed":
            return
        if state == "failed":
            raise GateError(f"CI didn't pass on {sha}, so nothing was published. Tag a commit on main that CI passed on.")
        if state == "missing" and waited >= appear_s:
            raise GateError(
                f"CI never ran on a push of {sha} to main, so nothing was published. "
                "Tag a commit on main once CI passes on it."
            )
        if waited >= wait_s:
            raise GateError(
                f"CI on {sha} was still running after {int(wait_s // 60)} minutes, so nothing was published. "
                "Re-run this workflow once it passes."
            )
        print(f"CI on {sha} is {state}; checking again in {int(poll_s)} s", flush=True)
        sleep(poll_s)


def decide(event_name: str, event: dict, ref: str, sha: str, repo: str, api: Api, **wait: Any) -> dict[str, str]:
    """The channel and latest outputs for this push."""
    if event_name != "push":
        raise GateError(f"images publish only from a push, not {event_name or 'an unknown event'}")
    if event.get("deleted"):
        print(f"{ref} was deleted, so there's nothing to publish")
        return {"channel": "none", "latest": "false"}
    if ref == f"refs/heads/{BRANCH}":
        return {"channel": "edge", "latest": "false"}
    if not ref.startswith(TAG_PREFIX):
        raise GateError(f"{ref or 'this ref'} isn't main or a release tag, so nothing was published")
    tag = ref[len(TAG_PREFIX):]
    if release_version(tag) is None:
        raise GateError(f"{tag} isn't a release tag (vMAJOR.MINOR.PATCH or vMAJOR.MINOR.PATCH-PRERELEASE), so nothing was published")
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise GateError("GITHUB_SHA or GITHUB_REPOSITORY doesn't look right, so nothing was published")
    wait_for_ci(lambda: ci_runs(api, repo, sha), sha, repo, **wait)
    latest = moves_latest(tag, release_tags(api, repo))
    return {"channel": "release", "latest": "true" if latest else "false"}


def next_link(header: str) -> str | None:
    """The rel="next" URL of a Link header, if there is one."""
    for part in header.split(","):
        target, _, params = part.partition(";")
        if re.search(r'\brel="?next"?', params):
            return target.strip().removeprefix("<").removesuffix(">")
    return None


def github_api(base_url: str, token: str) -> Api:
    """api(path, params) for the GitHub REST API. It follows pagination only
    within ``base_url``, so the token never goes anywhere else."""
    base = base_url.rstrip("/")

    def api(path: str, params: dict[str, str]) -> list[Any]:
        if not token:
            raise GateError("GH_TOKEN isn't set, so CI can't be checked and nothing was published")
        url: str | None = f"{base}/{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
        pages: list[Any] = []
        while url:
            if len(pages) >= MAX_PAGES or not url.startswith(base + "/"):
                raise GateError(f"the {path} lookup paginated unexpectedly, so nothing was published")
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "rounds-release-gate",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    pages.append(json.load(response))
                    url = next_link(response.headers.get("Link") or "")
            except (OSError, ValueError) as err:
                raise GateError(f"the {path} lookup failed ({err}), so nothing was published") from None
        return pages

    return api


def main() -> int:
    env = os.environ
    try:
        event: Any = {}
        if env.get("GITHUB_EVENT_PATH"):
            with open(env["GITHUB_EVENT_PATH"], encoding="utf-8") as fh:
                event = json.load(fh)
        if not isinstance(event, dict):
            raise GateError("the event payload isn't an object, so nothing was published")
        outputs = decide(
            env.get("GITHUB_EVENT_NAME", ""),
            event,
            env.get("GITHUB_REF", ""),
            env.get("GITHUB_SHA", ""),
            env.get("GITHUB_REPOSITORY", ""),
            github_api(env.get("GITHUB_API_URL") or "https://api.github.com", env.get("GH_TOKEN", "")),
        )
        output_path = env.get("GITHUB_OUTPUT")
        if not output_path:
            raise GateError("GITHUB_OUTPUT isn't set, so nothing was published")
        with open(output_path, "a", encoding="utf-8") as out:
            out.writelines(f"{key}={value}\n" for key, value in outputs.items())
    except (GateError, OSError, ValueError) as err:
        print(f"::error::{err}")
        return 1
    print(f"publishing channel={outputs['channel']} latest={outputs['latest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
