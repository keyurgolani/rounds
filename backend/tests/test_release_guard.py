"""Release guard (ROUNDS-00A-L01 stage 5).

Pushes to main publish sha-<short> and move edge. Only a v* tag publishes the
version tags and moves X.Y and latest, and only after CI passed on a push of
that exact commit to main; the gate fails closed. Builds push only tags that
never move; one job, one at a time across the repository, moves edge, X.Y,
and latest for all four images after every build passed. Pull requests into
main and next lint their migration changes, and CODEOWNERS routes the files
that decide all this to the owner."""
from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
import urllib.error
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
_spec = importlib.util.spec_from_file_location("release_gate", ROOT / "scripts" / "release_gate.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["release_gate"] = gate
_spec.loader.exec_module(gate)

REPO = "keyurgolani/rounds"
SHA = "a" * 40
OTHER_SHA = "b" * 40


def _workflow(name: str) -> dict:
    data = yaml.safe_load((WORKFLOWS / name).read_text())
    # YAML 1.1 reads the bare key `on` as True.
    data["on"] = data.pop(True, data.get("on"))
    return data


# ---- the publishing workflow ---------------------------------------------------------------


def test_every_workflow_parses():
    for path in sorted(WORKFLOWS.glob("*.yml")):
        assert isinstance(yaml.safe_load(path.read_text()), dict), path.name


def test_publishing_runs_only_on_pushes_to_main_and_v_tags():
    workflow = _workflow("publish-images.yml")
    assert workflow["on"] == {"push": {"branches": ["main"], "tags": ["v*"]}}
    assert "workflow_dispatch" not in (WORKFLOWS / "publish-images.yml").read_text()
    assert workflow["permissions"] == {"contents": "read"}


def test_builds_never_cancel_each_other_and_moving_tags_move_one_at_a_time():
    # A run-wide group per ref let a newer push cancel an older one's pending
    # publish, so that commit's sha-<short> never published.
    workflow = _workflow("publish-images.yml")
    assert "concurrency" not in workflow
    jobs = workflow["jobs"]
    assert "concurrency" not in jobs["plan"]
    build = jobs["publish"]["concurrency"]
    assert build == {
        "group": "publish-images-build-${{ github.ref }}-${{ github.sha }}-${{ matrix.service }}",
        "cancel-in-progress": False,
    }
    # One group per channel for the whole repository, with no per-ref or
    # per-commit part. edge and the release tags never share a tag, and a
    # waiting release job can't be replaced by an edge one.
    assert jobs["move-tags"]["concurrency"] == {
        "group": "publish-images-moving-tags-${{ needs.plan.outputs.channel }}",
        "cancel-in-progress": False,
    }


def test_the_plan_job_gates_publishing_and_holds_no_publishing_rights():
    jobs = _workflow("publish-images.yml")["jobs"]
    plan, publish = jobs["plan"], jobs["publish"]
    assert plan["permissions"] == {"actions": "read", "contents": "read"}
    assert "secrets." not in json.dumps(plan)
    assert [s.get("run") for s in plan["steps"] if "run" in s] == ["python3 scripts/release_gate.py plan"]
    assert plan["outputs"] == {"channel": "${{ steps.plan.outputs.channel }}"}
    assert publish["needs"] == "plan"
    assert publish["if"] == "needs.plan.outputs.channel == 'edge' || needs.plan.outputs.channel == 'release'"
    assert publish["permissions"] == {"contents": "read", "packages": "write"}
    move = jobs["move-tags"]
    # Needing the matrix job means every one of the four builds passed.
    assert move["needs"] == ["plan", "publish"]
    assert move["if"] == publish["if"]
    assert move["permissions"] == {"contents": "read", "packages": "write"}
    assert set(jobs) == {"plan", "publish", "move-tags"}


def _publish_steps() -> list[dict]:
    return _workflow("publish-images.yml")["jobs"]["publish"]["steps"]


def test_each_build_pushes_only_the_tags_the_gate_decided():
    steps = _publish_steps()
    names = [s.get("name") or s.get("uses") for s in steps]
    tags = next(s for s in steps if s.get("id") == "tags")
    assert tags["run"] == "python3 scripts/release_gate.py tags"
    assert tags["env"] == {"CHANNEL": "${{ needs.plan.outputs.channel }}"}
    metadata = [s for s in steps if str(s.get("uses", "")).startswith("docker/metadata-action")]
    assert len(metadata) == 2
    for step in metadata:
        assert names.index(step["name"]) > names.index(tags["name"])
        assert step["with"]["flavor"] == "latest=false"
        assert step["with"]["tags"] == "${{ steps.tags.outputs.tags }}"
    text = (WORKFLOWS / "publish-images.yml").read_text()
    assert "is_default_branch" not in text and "event=branch" not in text
    # No moving tag is written into a build.
    build = json.dumps(_workflow("publish-images.yml")["jobs"]["publish"])
    assert "value=edge" not in build and "value=latest" not in build and "{{major}}.{{minor}}" not in build


def _move_steps() -> list[dict]:
    return _workflow("publish-images.yml")["jobs"]["move-tags"]["steps"]


def test_the_moving_tags_move_without_a_rebuild_decided_right_before_they_move():
    steps = _move_steps()
    assert not any("build-push-action" in str(s.get("uses", "")) for s in steps)
    assert not any("metadata-action" in str(s.get("uses", "")) for s in steps)
    move = steps[-1]
    assert move["name"] == "Move edge, X.Y, and latest"
    assert move["run"] == "python3 scripts/release_gate.py retag"
    assert move["env"] == {
        "CHANNEL": "${{ needs.plan.outputs.channel }}",
        "GH_TOKEN": "${{ github.token }}",
        "GHCR_PREFIX": "${{ env.GHCR_REGISTRY }}/${{ github.repository }}",
        "DOCKERHUB_PREFIX": (
            "${{ steps.dockerhub.outputs.configured == 'true' && "
            "format('docker.io/{0}/rounds', env.DOCKERHUB_NAMESPACE) || '' }}"
        ),
    }
    # The prefixes name what the builds push: <prefix>-<service>.
    publish = _workflow("publish-images.yml")["jobs"]["publish"]
    images = [s["with"]["images"] for s in publish["steps"] if str(s.get("uses", "")).startswith("docker/metadata-action")]
    assert images == [
        "${{ env.GHCR_REGISTRY }}/${{ github.repository }}-${{ matrix.image }}",
        "docker.io/${{ env.DOCKERHUB_NAMESPACE }}/rounds-${{ matrix.image }}",
    ]
    assert [entry["image"] for entry in publish["strategy"]["matrix"]["include"]] == list(gate.IMAGES)


def test_docker_hub_stays_optional_and_its_secrets_reach_only_the_steps_that_use_them():
    publish = _workflow("publish-images.yml")["jobs"]["publish"]
    steps = {s.get("name"): s for s in publish["steps"]}
    configured = "steps.dockerhub.outputs.configured == 'true'"
    assert steps["Log in to Docker Hub"]["if"] == configured
    assert steps["Extract Docker Hub metadata"]["if"] == configured
    assert steps["Build and push ${{ matrix.service }} to Docker Hub"]["if"] == configured
    assert steps["Docker Hub publish skipped"]["if"] == "steps.dockerhub.outputs.configured != 'true'"
    check = steps["Check for Docker Hub credentials"]
    assert check["id"] == "dockerhub" and set(check["env"]) == {"DOCKERHUB_USERNAME", "DOCKERHUB_TOKEN"}
    holders = {name for name, step in steps.items() if "secrets.DOCKERHUB" in json.dumps(step)}
    assert holders == {"Check for Docker Hub credentials", "Log in to Docker Hub"}
    assert "secrets." not in json.dumps(publish.get("env", {}))

    move = _workflow("publish-images.yml")["jobs"]["move-tags"]
    move_steps = {s.get("name"): s for s in move["steps"]}
    assert move_steps["Log in to Docker Hub"]["if"] == configured
    check = move_steps["Check for Docker Hub credentials"]
    assert check["id"] == "dockerhub" and set(check["env"]) == {"DOCKERHUB_USERNAME", "DOCKERHUB_TOKEN"}
    holders = {name for name, step in move_steps.items() if "secrets.DOCKERHUB" in json.dumps(step)}
    assert holders == {"Check for Docker Hub credentials", "Log in to Docker Hub"}
    assert "secrets." not in json.dumps(move.get("env", {}))


def test_every_action_the_publish_workflow_runs_is_pinned_to_a_commit():
    uses = [line.strip() for line in (WORKFLOWS / "publish-images.yml").read_text().splitlines() if "uses:" in line]
    assert len(uses) == 13
    for line in uses:
        assert re.fullmatch(r"(- )?uses: [\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d+\.\d+\.\d+", line), line


def test_codeowners_routes_the_release_and_migration_files_to_the_owner():
    lines = [line.split() for line in (ROOT / ".github" / "CODEOWNERS").read_text().splitlines() if line.strip() and not line.startswith("#")]
    owners = {path: rest for path, *rest in lines}
    for path in (
        "/pocketbase/pb_migrations/",
        "/scripts/migration-lint-allowlist.json",
        "/scripts/lint_migrations.py",
        "/scripts/release_gate.py",
        "/.github/workflows/",
        "/.github/CODEOWNERS",
    ):
        assert owners.get(path) == ["@keyurgolani"], path


# ---- installs pin the tag they run -----------------------------------------------------------


def test_compose_takes_one_image_tag_and_defaults_to_latest():
    compose = yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text())
    images = {name: svc["image"] for name, svc in compose["services"].items() if "image" in svc}
    assert set(images) == {"frontend", "pocketbase", "runner", "pdf-renderer"}
    for name, image in images.items():
        variable = "ROUNDS_" + name.upper().replace("-", "_") + "_IMAGE"
        assert image == f"${{{variable}:-keyurgolani/rounds-{name}:${{ROUNDS_IMAGE_TAG:-latest}}}}", name


def test_k8s_pins_every_deployment_image_in_one_place():
    kustomization = yaml.safe_load((ROOT / "k8s" / "kustomization.yaml").read_text())
    pins = {entry["name"]: entry["newTag"] for entry in kustomization["images"]}
    images = []
    for manifest in kustomization["resources"]:
        for doc in yaml.safe_load_all((ROOT / "k8s" / manifest).read_text()):
            if doc and doc.get("kind") == "Deployment":
                images += [c["image"] for c in doc["spec"]["template"]["spec"]["containers"]]
    assert len(images) == 3
    for image in images:
        name, _, tag = image.rpartition(":")
        # The pin repeats the manifests' tag, so applying the base runs what it ran before.
        assert pins.get(name) == tag, image
    assert set(pins) == {image.rpartition(":")[0] for image in images}


# ---- the migration lint job ------------------------------------------------------------------


def test_pull_requests_into_main_and_next_lint_their_migrations_read_only():
    workflow = _workflow("ci.yml")
    assert "pull_request" in workflow["on"]
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["migrations"]
    assert job["if"] == "github.event_name == 'pull_request' && (github.base_ref == 'main' || github.base_ref == 'next')"
    assert "permissions" not in job and "secrets." not in json.dumps(job)
    checkout = job["steps"][0]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"] == {"fetch-depth": 0, "persist-credentials": False}
    assert job["steps"][-1]["run"] == "python scripts/lint_migrations.py --base HEAD^1 --head HEAD"


# ---- the release gate ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tag, version",
    [
        ("v1.2.3", ((1, 2, 3), True)),
        ("v0.10.0", ((0, 10, 0), True)),
        ("v2.0.0-rc.1", ((2, 0, 0), False)),
        ("v1.2", None),
        ("1.2.3", None),
        ("v01.2.3", None),
        ("v1.2.3+build", None),
        ("v1.2.3-", None),
        ("vnext", None),
    ],
)
def test_release_tags_are_strict_semver(tag, version):
    assert gate.release_version(tag) == version


def _bare(tag: str) -> str:
    return tag.removeprefix("v").split("-")[0]


@pytest.mark.parametrize(
    "tag, tags, moves",
    [
        ("v1.2.0", ["v1.0.0", "v1.1.5", "v1.2.0"], True),
        ("v1.10.0", ["v1.9.0", "v1.10.0"], True),
        ("v1.0.1", ["v1.1.0", "v1.0.1"], False),
        ("v2.0.0-rc.1", ["v1.0.0", "v2.0.0-rc.1"], False),
        ("v1.1.0", ["v1.1.0", "v2.0.0-rc.1", "not-a-release"], True),
    ],
)
def test_latest_moves_only_to_the_highest_stable_version(tag, tags, moves):
    assert (gate.highest_stable(tags) == _bare(tag)) is moves


@pytest.mark.parametrize(
    "tag, tags, moves",
    [
        ("v1.2.3", ["v1.2.2", "v1.2.3", "v1.3.0"], True),
        ("v1.2.2", ["v1.2.2", "v1.2.3"], False),
        ("v1.2.10", ["v1.2.9", "v1.2.10"], True),
        ("v1.2.4-rc.1", ["v1.2.3", "v1.2.4-rc.1"], False),
        ("v1.2.3", ["v1.2.3", "v1.2.4-rc.1", "v2.2.9"], True),
    ],
)
def test_x_y_moves_only_to_the_highest_stable_patch_of_its_line(tag, tags, moves):
    (major, minor, _), _stable = gate.release_version(tag)
    assert (gate.highest_stable(tags, (major, minor)) == _bare(tag)) is moves


def test_no_stable_version_means_no_target():
    assert gate.highest_stable([]) is None
    assert gate.highest_stable(["v2.0.0-rc.1", "not-a-release"]) is None
    assert gate.highest_stable(["v1.2.3"], (1, 3)) is None


def _run(status="completed", conclusion="success", sha=SHA, event="push", branch="main", repo=REPO):
    return {"head_sha": sha, "event": event, "head_branch": branch, "status": status, "conclusion": conclusion,
            "head_repository": {"full_name": repo}}


@pytest.mark.parametrize(
    "runs, state",
    [
        ([_run()], "passed"),
        ([_run(conclusion="failure"), _run()], "passed"),
        ([_run(status="in_progress", conclusion=None)], "running"),
        ([_run(status="queued", conclusion=None), _run(conclusion="failure")], "running"),
        ([_run(conclusion="failure")], "failed"),
        ([_run(conclusion="cancelled")], "failed"),
        ([], "missing"),
        ([_run(sha=OTHER_SHA)], "missing"),
        ([_run(event="pull_request")], "missing"),
        ([_run(branch="next")], "missing"),
        ([_run(repo="someone/fork")], "missing"),
    ],
)
def test_only_a_successful_push_run_on_main_for_the_exact_commit_passes(runs, state):
    assert gate.ci_state(runs, SHA, REPO) == state


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _wait(states: list[list[dict]], **limits):
    clock = Clock()
    answers = iter(states)
    last = states[-1]
    gate.wait_for_ci(lambda: next(answers, last), SHA, REPO, clock=clock.time, sleep=clock.sleep, **limits)
    return clock


def test_the_gate_waits_while_ci_runs_then_passes():
    clock = _wait([[_run(status="in_progress", conclusion=None)]] * 3 + [[_run()]], poll_s=30)
    assert clock.slept == [30, 30, 30]


@pytest.mark.parametrize(
    "states, message",
    [
        ([[_run(conclusion="failure")]], "didn't pass"),
        ([[]], "never ran"),
        ([[_run(status="in_progress", conclusion=None)]], "still running"),
    ],
)
def test_the_gate_fails_closed(states, message):
    with pytest.raises(gate.GateError, match=message):
        _wait(states, wait_s=300, appear_s=60, poll_s=30)


def test_a_run_that_shows_up_late_still_counts():
    clock = _wait([[], [], [_run()]], appear_s=300, poll_s=30)
    assert clock.slept == [30, 30]


class FakeApi:
    def __init__(self, runs: list[dict], tags: list[str], tip: str = SHA) -> None:
        self.runs, self.tags, self.tip = runs, tags, tip
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, path: str, params: dict) -> list:
        self.calls.append((path, params))
        if path.endswith("/runs"):
            return [{"total_count": len(self.runs), "workflow_runs": self.runs}]
        if "/git/matching-refs/tags/" in path:
            return [[{"ref": f"refs/tags/{t}"} for t in self.tags]]
        if path.endswith("/git/ref/heads/main"):
            return [{"ref": "refs/heads/main", "object": {"sha": self.tip, "type": "commit"}}]
        raise AssertionError(path)


def _plan(ref, api, event=None, event_name="push", sha=SHA):
    clock = Clock()
    return gate.plan(event_name, event or {}, ref, sha, REPO, api, wait_s=60, appear_s=30, poll_s=30,
                     clock=clock.time, sleep=clock.sleep)


def test_a_push_to_main_is_the_edge_channel_without_asking_github():
    api = FakeApi([], [])
    assert _plan("refs/heads/main", api) == {"channel": "edge"}
    assert api.calls == []


def test_a_release_tag_publishes_once_ci_passed_on_that_commit():
    api = FakeApi([_run()], ["v1.0.0", "v1.1.0"])
    assert _plan("refs/tags/v1.1.0", api) == {"channel": "release"}
    path, params = api.calls[0]
    assert path == f"repos/{REPO}/actions/workflows/ci.yml/runs"
    assert params == {"head_sha": SHA, "event": "push", "branch": "main", "per_page": "100"}


# ---- the tags each build pushes, and where the moving tags point ----------------------------

VERSION_TAGS = ["type=semver,pattern={{version}}", "type=ref,event=tag"]


@pytest.mark.parametrize(
    "channel, ref, tags",
    [
        ("edge", "refs/heads/main", ["type=sha,prefix=sha-"]),
        ("release", "refs/tags/v1.2.0", VERSION_TAGS),
        ("release", "refs/tags/v1.3.0-rc.1", VERSION_TAGS),
    ],
)
def test_a_build_pushes_only_tags_that_never_move(channel, ref, tags):
    assert gate.image_tags(channel, ref, SHA, REPO) == tags


def test_edge_points_at_mains_tip():
    api = FakeApi([], [], tip=SHA)
    assert gate.moving_tags("edge", "refs/heads/main", SHA, REPO, api) == [("edge", "sha-aaaaaaa")]


def test_an_old_main_run_points_edge_at_the_tip_not_its_own_commit():
    # Re-running an old run, or one that lost the race, can't move edge back.
    api = FakeApi([], [], tip=OTHER_SHA)
    assert gate.image_tags("edge", "refs/heads/main", SHA, REPO) == ["type=sha,prefix=sha-"]
    assert gate.moving_tags("edge", "refs/heads/main", SHA, REPO, api) == [("edge", "sha-bbbbbbb")]


@pytest.mark.parametrize(
    "tag, tags, moving",
    [
        ("v1.2.0", ["v1.0.0", "v1.1.5", "v1.2.0"], [("1.0", "1.0.0"), ("1.1", "1.1.5"), ("1.2", "1.2.0"), ("latest", "1.2.0")]),
        ("v1.1.6", ["v1.1.5", "v1.1.6", "v1.2.0"], [("1.1", "1.1.6"), ("1.2", "1.2.0"), ("latest", "1.2.0")]),
        # An older patch leaves every tag at the highest versions.
        ("v1.1.4", ["v1.1.4", "v1.1.5", "v1.2.0"], [("1.1", "1.1.5"), ("1.2", "1.2.0"), ("latest", "1.2.0")]),
        ("v1.10.0", ["v1.9.3", "v1.10.0"], [("1.9", "1.9.3"), ("1.10", "1.10.0"), ("latest", "1.10.0")]),
    ],
)
def test_a_release_points_every_x_y_and_latest_at_the_highest_versions(tag, tags, moving):
    # Every line, so a newer release job that replaced a waiting one leaves
    # that one's line where it would have.
    api = FakeApi([], tags)
    assert gate.moving_tags("release", f"refs/tags/{tag}", SHA, REPO, api) == moving


def test_a_release_rechecks_the_tags_when_they_move():
    # A higher release that appeared after the plan job ran keeps latest.
    api = FakeApi([_run()], ["v1.1.0"])
    assert _plan("refs/tags/v1.1.0", api) == {"channel": "release"}
    api.tags = ["v1.1.0", "v1.2.0"]
    assert gate.moving_tags("release", "refs/tags/v1.1.0", SHA, REPO, api) == [
        ("1.1", "1.1.0"),
        ("1.2", "1.2.0"),
        ("latest", "1.2.0"),
    ]


@pytest.mark.parametrize(
    "tags, moving",
    [
        (["v1.2.0", "v1.3.0-rc.1", "v1.3.0-rc.2"], [("1.2", "1.2.0"), ("latest", "1.2.0")]),
        (["v1.3.0-rc.1"], []),
    ],
)
def test_a_pre_release_is_never_x_y_or_latest(tags, moving):
    api = FakeApi([], tags)
    assert gate.moving_tags("release", "refs/tags/v1.3.0-rc.1", SHA, REPO, api) == moving


@pytest.mark.parametrize(
    "channel, ref",
    [("none", "refs/heads/main"), ("", "refs/heads/main"), ("edge", "refs/tags/v1.0.0"), ("release", "refs/heads/main")],
)
def test_tags_for_anything_else_fail(channel, ref):
    with pytest.raises(gate.GateError):
        gate.image_tags(channel, ref, SHA, REPO)
    with pytest.raises(gate.GateError):
        gate.moving_tags(channel, ref, SHA, REPO, FakeApi([], ["v1.0.0"]))


def test_a_malformed_tip_fails():
    with pytest.raises(gate.GateError, match="unexpected shape"):
        gate.moving_tags("edge", "refs/heads/main", SHA, REPO, FakeApi([], [], tip="not-a-sha"))


# ---- moving the tags -------------------------------------------------------------------------

GHCR = "ghcr.io/keyurgolani/rounds"
HUB = "docker.io/keyurgolani/rounds"


class FakeDocker:
    """``docker buildx imagetools``: inspect answers for the refs in
    ``pushed``, and create records the tag it writes."""

    def __init__(self, pushed: set[str], fail_create: str | None = None) -> None:
        self.pushed, self.fail_create = set(pushed), fail_create
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> int:
        self.calls.append(args)
        assert args[:3] == ["docker", "buildx", "imagetools"], args
        if args[3] == "inspect":
            return 0 if args[4] in self.pushed else 1
        assert args[3:5] == ["create", "--tag"], args
        if args[5] == self.fail_create:
            return 1
        self.pushed.add(args[5])
        return 0

    def created(self) -> list[tuple[str, str]]:
        return [(c[5], c[6]) for c in self.calls if c[3] == "create"]


def _pushed(prefix: str, tag: str, images=gate.IMAGES) -> set[str]:
    return {f"{prefix}-{image}:{tag}" for image in images}


def test_each_tag_moves_for_all_four_images_on_every_registry():
    docker = FakeDocker(_pushed(GHCR, "1.2.0") | _pushed(HUB, "1.2.0"))
    moved = gate.retag([("1.2", "1.2.0"), ("latest", "1.2.0")], [GHCR, HUB], docker)
    assert moved == [f"{GHCR}-*:1.2 -> 1.2.0", f"{GHCR}-*:latest -> 1.2.0", f"{HUB}-*:1.2 -> 1.2.0", f"{HUB}-*:latest -> 1.2.0"]
    created = docker.created()
    assert len(created) == 16
    for prefix in (GHCR, HUB):
        for image in gate.IMAGES:
            for moving in ("1.2", "latest"):
                assert (f"{prefix}-{image}:{moving}", f"{prefix}-{image}:1.2.0") in created


def test_a_tag_stays_put_unless_every_image_has_its_target(capsys):
    # The tip's runner image isn't pushed yet, so edge moves for no image.
    docker = FakeDocker(_pushed(GHCR, "sha-bbbbbbb", images=("frontend", "pocketbase", "pdf-renderer")))
    assert gate.retag([("edge", "sha-bbbbbbb")], [GHCR], docker) == []
    assert docker.created() == []
    out = capsys.readouterr().out
    assert out.startswith("::warning::edge stays where it is") and f"{GHCR}-runner:sha-bbbbbbb" in out


def test_a_failed_move_fails_the_job():
    docker = FakeDocker(_pushed(GHCR, "sha-aaaaaaa"), fail_create=f"{GHCR}-runner:edge")
    with pytest.raises(gate.GateError, match="re-run"):
        gate.retag([("edge", "sha-aaaaaaa")], [GHCR], docker)


@pytest.mark.parametrize("prefix", ["", "ghcr.io", "ghcr.io/x y/rounds", "ghcr.io/owner/rounds;rm"])
def test_a_malformed_prefix_moves_nothing(prefix):
    docker = FakeDocker(set())
    with pytest.raises(gate.GateError, match="prefix"):
        gate.retag([("edge", "sha-aaaaaaa")], [prefix], docker)
    assert docker.calls == []


def test_a_prefix_is_lowercased_the_way_the_builds_name_images():
    docker = FakeDocker(_pushed(GHCR, "sha-aaaaaaa"))
    assert gate.retag([("edge", "sha-aaaaaaa")], ["GHCR.io/KeyurGolani/Rounds"], docker) == [f"{GHCR}-*:edge -> sha-aaaaaaa"]


@pytest.mark.parametrize(
    "ref, event_name",
    [
        ("refs/heads/next", "push"),
        ("refs/heads/feature", "push"),
        ("refs/tags/vnext", "push"),
        ("refs/tags/release-1", "push"),
        ("refs/heads/main", "workflow_dispatch"),
        ("refs/tags/v1.0.0", "workflow_dispatch"),
    ],
)
def test_anything_else_publishes_nothing_and_fails(ref, event_name):
    api = FakeApi([_run()], ["v1.0.0"])
    with pytest.raises(gate.GateError):
        _plan(ref, api, event_name=event_name)
    assert api.calls == []


def test_a_tag_whose_commit_ci_never_passed_fails():
    api = FakeApi([_run(sha=OTHER_SHA), _run(conclusion="failure")], ["v1.0.0"])
    with pytest.raises(gate.GateError, match="didn't pass"):
        _plan("refs/tags/v1.0.0", api)


def test_a_deleted_tag_publishes_nothing():
    api = FakeApi([_run()], [])
    assert _plan("refs/tags/v1.0.0", api, event={"deleted": True}) == {"channel": "none"}
    assert api.calls == []


@pytest.mark.parametrize("sha", ["", "abc", "A" * 40])
def test_a_malformed_commit_fails(sha):
    with pytest.raises(gate.GateError):
        _plan("refs/tags/v1.0.0", FakeApi([_run(sha=sha)], []), sha=sha)
    with pytest.raises(gate.GateError):
        gate.image_tags("edge", "refs/heads/main", sha, REPO)
    with pytest.raises(gate.GateError):
        gate.moving_tags("edge", "refs/heads/main", sha, REPO, FakeApi([], [], tip=SHA))


# ---- the GitHub client -----------------------------------------------------------------------


class FakeResponse(io.BytesIO):
    def __init__(self, body, link: str = "") -> None:
        super().__init__(json.dumps(body).encode())
        self.headers = {"Link": link} if link else {}

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def test_the_client_follows_pages_only_on_the_api_host(monkeypatch):
    base = "https://api.github.com"
    pages = {
        f"{base}/repos/{REPO}/x?per_page=100": FakeResponse([1], link=f'<{base}/repos/{REPO}/x?page=2>; rel="next"'),
        f"{base}/repos/{REPO}/x?page=2": FakeResponse([2]),
    }
    seen: list = []

    def urlopen(request, timeout):
        seen.append((request.full_url, request.get_header("Authorization")))
        return pages[request.full_url]

    monkeypatch.setattr(gate.urllib.request, "urlopen", urlopen)
    assert gate.github_api(base, "test-token")(f"repos/{REPO}/x", {"per_page": "100"}) == [[1], [2]]
    assert [auth for _url, auth in seen] == ["Bearer test-token"] * 2

    elsewhere = FakeResponse([1], link='<https://example.com/steal>; rel="next"')
    monkeypatch.setattr(gate.urllib.request, "urlopen", lambda request, timeout: elsewhere)
    with pytest.raises(gate.GateError, match="paginated unexpectedly"):
        gate.github_api(base, "test-token")(f"repos/{REPO}/x", {})


def test_a_failed_lookup_or_a_missing_token_fails_closed(monkeypatch):
    def refuse(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(gate.urllib.request, "urlopen", refuse)
    with pytest.raises(gate.GateError, match="lookup failed"):
        gate.github_api("https://api.github.com", "test-token")("repos/x/y/z", {})
    with pytest.raises(gate.GateError, match="GH_TOKEN"):
        gate.github_api("https://api.github.com", "")("repos/x/y/z", {})


@pytest.fixture
def actions_env(tmp_path, monkeypatch):
    """The environment Actions gives a step; returns its GITHUB_OUTPUT file."""
    output, event = tmp_path / "output", tmp_path / "event.json"
    event.write_text("{}")
    for key, value in {
        "GITHUB_EVENT_NAME": "push", "GITHUB_EVENT_PATH": str(event), "GITHUB_REF": "refs/heads/main",
        "GITHUB_SHA": SHA, "GITHUB_REPOSITORY": REPO, "GITHUB_OUTPUT": str(output),
    }.items():
        monkeypatch.setenv(key, value)
    return output


def test_plan_writes_the_channel_for_a_push_to_main(actions_env):
    assert gate.main(["plan"]) == 0
    assert actions_env.read_text() == "channel=edge\n"


def test_tags_writes_a_multi_line_output(actions_env, monkeypatch):
    monkeypatch.setenv("CHANNEL", "release")
    monkeypatch.setenv("GITHUB_REF", "refs/tags/v1.2.0")
    assert gate.main(["tags"]) == 0
    first, *body, last = actions_env.read_text().splitlines()
    delimiter = first.removeprefix("tags<<")
    assert first.startswith("tags<<ghadelimiter_") and last == delimiter
    assert body == VERSION_TAGS


@pytest.mark.parametrize(
    "hub, prefixes",
    [("", [GHCR]), (HUB, [GHCR, HUB])],
)
def test_retag_moves_edge_on_each_configured_registry(actions_env, monkeypatch, capsys, hub, prefixes):
    monkeypatch.setenv("CHANNEL", "edge")
    monkeypatch.setenv("GHCR_PREFIX", GHCR)
    monkeypatch.setenv("DOCKERHUB_PREFIX", hub)
    monkeypatch.setattr(gate, "github_api", lambda base, token: FakeApi([], [], tip=SHA))
    docker = FakeDocker(_pushed(GHCR, "sha-aaaaaaa") | _pushed(HUB, "sha-aaaaaaa"))
    assert gate.main(["retag"], run=docker) == 0
    created = docker.created()
    assert {p for p in (GHCR, HUB) for tag, _source in created if tag.startswith(p + "-")} == set(prefixes)
    assert len(created) == 4 * len(prefixes)
    assert all(tag.endswith(":edge") and source.endswith(":sha-aaaaaaa") for tag, source in created)
    assert not actions_env.exists()
    assert "moved: " in capsys.readouterr().out


def test_retag_fails_without_a_ghcr_prefix(actions_env, monkeypatch):
    monkeypatch.setenv("CHANNEL", "edge")
    monkeypatch.delenv("GHCR_PREFIX", raising=False)
    monkeypatch.delenv("DOCKERHUB_PREFIX", raising=False)
    monkeypatch.setattr(gate, "github_api", lambda base, token: FakeApi([], [], tip=SHA))
    docker = FakeDocker(set())
    assert gate.main(["retag"], run=docker) == 1
    assert docker.calls == []


def test_main_fails_without_outputs_when_the_gate_refuses(actions_env, monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REF", "refs/tags/v1.0.0")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert gate.main(["plan"]) == 1
    assert not actions_env.exists()
    assert capsys.readouterr().out.startswith("::error::")


@pytest.mark.parametrize("argv", [[], ["publish"], ["plan", "extra"]])
def test_main_needs_a_command(actions_env, argv):
    assert gate.main(argv) == 1
    assert not actions_env.exists()
