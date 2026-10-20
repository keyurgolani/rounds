#!/usr/bin/env python3
"""Decides what a push may publish (ROUNDS-00A-L01 stage 5).

The image workflow runs this twice:

``plan``, in the plan job, before anything builds
    A push to main is the edge channel. A ``vX.Y.Z`` or
    ``vX.Y.Z-PRERELEASE`` tag is the release channel, but only once the
    ``CI`` workflow passed on a push of the exact tagged commit to main. It
    waits while that run is still going and fails closed when no run
    passed, none ran, or the lookup failed. Anything else publishes nothing;
    a deleted ref isn't an error. Writes ``channel`` (edge, release, or
    none).

``tags``, in each publish job, right before it pushes
    Writes ``tags``, the docker/metadata-action tag list, from the
    repository as it is at that moment, so a re-run of an old run can't
    move a moving tag backwards:

    - edge: ``sha-<short>``, plus ``edge`` while this commit is still
      main's tip;
    - release: ``X.Y.Z`` and ``vX.Y.Z``, plus ``X.Y`` for the highest stable
      patch of that line and ``latest`` for the highest stable version.

Both read GITHUB_EVENT_NAME, GITHUB_EVENT_PATH, GITHUB_REF, GITHUB_SHA,
GITHUB_REPOSITORY, GITHUB_API_URL, GH_TOKEN, and GITHUB_OUTPUT; ``tags``
also reads CHANNEL, the plan job's channel.

usage: release_gate.py plan|tags
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
import uuid
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


# ---- versions ----------------------------------------------------------------------


def release_version(tag: str) -> tuple[tuple[int, int, int], bool] | None:
    """The tag's (major, minor, patch) and whether it is stable, or None
    when it isn't a release tag."""
    match = RELEASE_TAG.fullmatch(tag)
    if match is None:
        return None
    return (int(match[1]), int(match[2]), int(match[3])), match[4] is None


def _stable(tags: list[str]) -> list[tuple[int, int, int]]:
    return [v[0] for v in map(release_version, tags) if v is not None and v[1]]


def moves_latest(tag: str, tags: list[str]) -> bool:
    """Whether ``tag`` is a stable version that no other stable tag outranks."""
    mine = release_version(tag)
    if mine is None or not mine[1]:
        return False
    return all(mine[0] >= other for other in _stable(tags))


def moves_minor(tag: str, tags: list[str]) -> bool:
    """Whether ``tag`` is a stable version that no other stable tag of the
    same major and minor outranks, so it may move ``X.Y``."""
    mine = release_version(tag)
    if mine is None or not mine[1]:
        return False
    return all(mine[0] >= other for other in _stable(tags) if other[:2] == mine[0][:2])


# ---- GitHub lookups ----------------------------------------------------------------


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


def branch_tip(api: Api, repo: str) -> str:
    pages = api(f"repos/{repo}/git/ref/heads/{BRANCH}", {})
    target = pages[0].get("object") if pages and isinstance(pages[0], dict) else None
    sha = target.get("sha") if isinstance(target, dict) else None
    if not isinstance(sha, str):
        raise GateError(f"the {BRANCH} lookup answered in an unexpected shape, so nothing was published")
    return sha


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


# ---- the two commands --------------------------------------------------------------


def _check_identity(sha: str, repo: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise GateError("GITHUB_SHA or GITHUB_REPOSITORY doesn't look right, so nothing was published")


def _release_tag(ref: str) -> str:
    if not ref.startswith(TAG_PREFIX):
        raise GateError(f"{ref or 'this ref'} isn't main or a release tag, so nothing was published")
    tag = ref[len(TAG_PREFIX):]
    if release_version(tag) is None:
        raise GateError(f"{tag} isn't a release tag (vMAJOR.MINOR.PATCH or vMAJOR.MINOR.PATCH-PRERELEASE), so nothing was published")
    return tag


def plan(event_name: str, event: dict, ref: str, sha: str, repo: str, api: Api, **wait: Any) -> dict[str, str]:
    """The channel this push publishes on."""
    if event_name != "push":
        raise GateError(f"images publish only from a push, not {event_name or 'an unknown event'}")
    if event.get("deleted"):
        print(f"{ref} was deleted, so there's nothing to publish")
        return {"channel": "none"}
    if ref == f"refs/heads/{BRANCH}":
        return {"channel": "edge"}
    _release_tag(ref)
    _check_identity(sha, repo)
    wait_for_ci(lambda: ci_runs(api, repo, sha), sha, repo, **wait)
    return {"channel": "release"}


def image_tags(channel: str, ref: str, sha: str, repo: str, api: Api) -> list[str]:
    """The docker/metadata-action tag list for this publish, decided from
    the repository as it is now."""
    _check_identity(sha, repo)
    if channel == "edge":
        if ref != f"refs/heads/{BRANCH}":
            raise GateError(f"the edge channel publishes only from {BRANCH}, not {ref}")
        tags = ["type=sha,prefix=sha-"]
        if branch_tip(api, repo) == sha:
            tags.insert(0, "type=raw,value=edge")
        else:
            print(f"{sha} is no longer the tip of {BRANCH}, so edge stays where it is")
        return tags
    if channel == "release":
        tag = _release_tag(ref)
        existing = release_tags(api, repo)
        tags = ["type=semver,pattern={{version}}", "type=ref,event=tag"]
        if moves_minor(tag, existing):
            tags.append("type=semver,pattern={{major}}.{{minor}}")
        if moves_latest(tag, existing):
            tags.append("type=raw,value=latest")
        return tags
    raise GateError(f"there's nothing to publish on the {channel or 'unknown'} channel")


# ---- GitHub client and entry point -------------------------------------------------


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
            raise GateError("GH_TOKEN isn't set, so the lookup can't run and nothing was published")
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


def _write_outputs(path: str | None, outputs: dict[str, str | list[str]]) -> None:
    if not path:
        raise GateError("GITHUB_OUTPUT isn't set, so nothing was published")
    with open(path, "a", encoding="utf-8") as out:
        for key, value in outputs.items():
            if isinstance(value, list):
                delimiter = f"ghadelimiter_{uuid.uuid4().hex}"
                out.write(f"{key}<<{delimiter}\n" + "".join(f"{line}\n" for line in value) + f"{delimiter}\n")
            else:
                out.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    env = os.environ
    try:
        if args not in (["plan"], ["tags"]):
            raise GateError("usage: release_gate.py plan|tags")
        api = github_api(env.get("GITHUB_API_URL") or "https://api.github.com", env.get("GH_TOKEN", ""))
        ref, sha, repo = env.get("GITHUB_REF", ""), env.get("GITHUB_SHA", ""), env.get("GITHUB_REPOSITORY", "")
        outputs: dict[str, str | list[str]]
        if args == ["plan"]:
            event: Any = {}
            if env.get("GITHUB_EVENT_PATH"):
                with open(env["GITHUB_EVENT_PATH"], encoding="utf-8") as fh:
                    event = json.load(fh)
            if not isinstance(event, dict):
                raise GateError("the event payload isn't an object, so nothing was published")
            outputs = dict(plan(env.get("GITHUB_EVENT_NAME", ""), event, ref, sha, repo, api))
        else:
            outputs = {"tags": image_tags(env.get("CHANNEL", ""), ref, sha, repo, api)}
        _write_outputs(env.get("GITHUB_OUTPUT"), outputs)
    except (GateError, OSError, ValueError) as err:
        print(f"::error::{err}")
        return 1
    for key, value in outputs.items():
        print(f"{key}: {', '.join(value) if isinstance(value, list) else value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
