#!/usr/bin/env python3
"""Decides what a push may publish (ROUNDS-00A-L01 stage 5).

The image workflow runs this three times:

``plan``, in the plan job, before anything builds
    A push to main is the edge channel. A ``vX.Y.Z`` or
    ``vX.Y.Z-PRERELEASE`` tag is the release channel, but only once the
    ``CI`` workflow passed on a push of the exact tagged commit to main. It
    waits while that run is still going and fails closed when no run
    passed, none ran, or the lookup failed. Anything else publishes nothing;
    a deleted ref isn't an error. Writes ``channel`` (edge, release, or
    none).

``tags``, in each build job
    Writes ``tags``, the docker/metadata-action tag list. A build pushes
    only tags that never move: ``sha-<short>`` on the edge channel, and
    ``X.Y.Z`` and ``vX.Y.Z`` on the release channel.

``retag``, in the one job that runs after all four builds
    Decides the moving tags from the repository as it is at that moment and
    moves them for all four images together with ``docker buildx imagetools
    create``, without a rebuild:

    - edge: ``edge`` points at main's current tip;
    - release: each line's ``X.Y`` points at its highest stable patch and
      ``latest`` at the highest stable version. A pre-release is never one
      of them.

    A tag moves only when all four images already have the tag it points
    at; otherwise it stays where it is. Every run of a channel decides the
    same answer from the same repository, and the workflow runs each
    channel's jobs one at a time, so whichever runs last leaves each tag
    right, and an older publish can't move one backwards.

All three read GITHUB_REF, GITHUB_SHA, and GITHUB_REPOSITORY. ``plan`` and
``retag`` also read GITHUB_API_URL and GH_TOKEN, ``plan`` reads
GITHUB_EVENT_NAME and GITHUB_EVENT_PATH, ``plan`` and ``tags`` write
GITHUB_OUTPUT, ``tags`` and ``retag`` read CHANNEL, the plan job's channel,
and ``retag`` reads GHCR_PREFIX and DOCKERHUB_PREFIX, each a registry's image
name without its ``-<service>`` suffix (an empty one is skipped).

usage: release_gate.py plan|tags|retag
exit status: 0 decided, 1 nothing may publish or a move failed
"""
from __future__ import annotations

import json
import os
import re
import subprocess
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
# The four images every publish builds, as the workflow's matrix names them.
IMAGES = ("frontend", "pocketbase", "runner", "pdf-renderer")
# docker/metadata-action's type=sha tag uses the commit's first 7 characters.
SHORT_SHA = 7
IMAGE_PREFIX = re.compile(r"[a-z0-9.-]+(?::[0-9]+)?(?:/[a-z0-9._-]+)+")

# api(path, params) returns the decoded JSON of each page.
Api = Callable[[str, "dict[str, str]"], "list[Any]"]
# run(args) runs a command and returns its exit status.
Runner = Callable[["list[str]"], int]


class GateError(Exception):
    """Nothing may publish, or a tag didn't move; exit status 1."""


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


def highest_stable(tags: list[str], line: tuple[int, int] | None = None) -> str | None:
    """The highest stable version among ``tags`` as ``X.Y.Z``, the form the
    images carry, within the ``(major, minor)`` line when one is given."""
    versions = [v for v in _stable(tags) if line is None or v[:2] == line]
    return ".".join(map(str, max(versions))) if versions else None


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
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
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


# ---- the three commands -------------------------------------------------------------


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


def _edge_ref(ref: str) -> None:
    if ref != f"refs/heads/{BRANCH}":
        raise GateError(f"the edge channel publishes only from {BRANCH}, not {ref}")


def image_tags(channel: str, ref: str, sha: str, repo: str) -> list[str]:
    """The docker/metadata-action tag list a build pushes. None of these
    tags ever moves; ``moving_tags`` decides the ones that do."""
    _check_identity(sha, repo)
    if channel == "edge":
        _edge_ref(ref)
        return ["type=sha,prefix=sha-"]
    if channel == "release":
        _release_tag(ref)
        return ["type=semver,pattern={{version}}", "type=ref,event=tag"]
    raise GateError(f"there's nothing to publish on the {channel or 'unknown'} channel")


def moving_tags(channel: str, ref: str, sha: str, repo: str, api: Api) -> list[tuple[str, str]]:
    """``(moving tag, the tag it points at)`` for this publish, decided from
    the repository as it is now rather than from this run's own commit or
    tag, so every run decides the same answer."""
    _check_identity(sha, repo)
    if channel == "edge":
        _edge_ref(ref)
        tip = branch_tip(api, repo)
        if tip != sha:
            print(f"{sha} is no longer the tip of {BRANCH}, so edge follows the tip, {tip}")
        return [("edge", f"sha-{tip[:SHORT_SHA]}")]
    if channel == "release":
        # Every line's X.Y and latest, not just this tag's: a newer release
        # job can replace this one while it waits, and then it has to leave
        # the tags this one would have. A pre-release is never a target.
        _release_tag(ref)
        existing = release_tags(api, repo)
        moves: list[tuple[str, str]] = []
        for major, minor in sorted({version[:2] for version in _stable(existing)}):
            moves.append((f"{major}.{minor}", str(highest_stable(existing, (major, minor)))))
        top = highest_stable(existing)
        if top is not None:
            moves.append(("latest", top))
        return moves
    raise GateError(f"there's nothing to publish on the {channel or 'unknown'} channel")


def _image_prefix(prefix: str) -> str:
    # Registries take lowercase names, and docker/metadata-action lowercases
    # the names the builds push.
    prefix = prefix.lower()
    if not IMAGE_PREFIX.fullmatch(prefix):
        raise GateError("an image prefix doesn't look right, so no tag moved")
    return prefix


def retag(moves: list[tuple[str, str]], prefixes: list[str], run: Runner) -> list[str]:
    """Points each moving tag at its target on every registry prefix, for
    all four images together, and returns what moved. A tag whose target
    some image doesn't have yet stays where it is, with a warning."""
    moved: list[str] = []
    for prefix in map(_image_prefix, prefixes):
        for moving, target in moves:
            sources = [f"{prefix}-{image}:{target}" for image in IMAGES]
            missing = [s for s in sources if run(["docker", "buildx", "imagetools", "inspect", s]) != 0]
            if missing:
                print(
                    f"::warning::{moving} stays where it is on {prefix}: "
                    f"{', '.join(missing)} can't be read, so it isn't pushed for every image yet"
                )
                continue
            for image, source in zip(IMAGES, sources):
                if run(["docker", "buildx", "imagetools", "create", "--tag", f"{prefix}-{image}:{moving}", source]) != 0:
                    raise GateError(f"moving {moving} on {prefix}-{image} failed; re-run this job")
            moved.append(f"{prefix}-*:{moving} -> {target}")
    return moved


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


def run_command(args: list[str]) -> int:
    """Runs a docker command with its output in the job log, except an
    inspect's manifest."""
    quiet = args[:4] == ["docker", "buildx", "imagetools", "inspect"]
    return subprocess.run(args, check=False, stdout=subprocess.DEVNULL if quiet else None).returncode


def main(argv: list[str] | None = None, run: Runner = run_command) -> int:
    args = sys.argv[1:] if argv is None else argv
    env = os.environ
    try:
        if args not in (["plan"], ["tags"], ["retag"]):
            raise GateError("usage: release_gate.py plan|tags|retag")
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
        elif args == ["tags"]:
            outputs = {"tags": image_tags(env.get("CHANNEL", ""), ref, sha, repo)}
        else:
            moves = moving_tags(env.get("CHANNEL", ""), ref, sha, repo, api)
            prefixes = [p for p in (env.get("GHCR_PREFIX", ""), env.get("DOCKERHUB_PREFIX", "")) if p]
            if not prefixes:
                raise GateError("GHCR_PREFIX isn't set, so no tag moved")
            moved = retag(moves, prefixes, run)
            print("moved: " + ("; ".join(moved) if moved else "nothing"))
            return 0
        _write_outputs(env.get("GITHUB_OUTPUT"), outputs)
    except (GateError, OSError, ValueError) as err:
        print(f"::error::{err}")
        return 1
    for key, value in outputs.items():
        print(f"{key}: {', '.join(value) if isinstance(value, list) else value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
