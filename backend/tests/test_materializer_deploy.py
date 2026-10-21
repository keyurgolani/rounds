"""How the Legacy Artifact Snapshot materializer deploys (ROUNDS-00A-L04, PR 1).

It runs non-root, read-only, and secret-free in both compose files, the
image matrix, and k8s, and only PocketBase reaches it: in Compose over the
internal `materialize` network, and in k8s through a NetworkPolicy that
admits pods labeled rounds.io/net: pocketbase and allows no egress. Its
image builds from the repository root through an ignore file that admits
only the materializer and the frontend sources it bundles. Harness phase 7b
shows the Compose reachability at runtime.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MATERIALIZER = ROOT / "backend" / "materializer"
COMPOSE_FILES = ["docker-compose.yml", "docker-compose.prod.yml", "harness/compose.yml"]
# The frontend sources the bundle needs, and the package file whose module
# type esbuild reads; nothing else.
BUNDLED = [
    "frontend/src/features/resume/templates/",
    "frontend/src/features/resume/types.ts",
    "frontend/src/features/resume/utils.ts",
    "frontend/src/features/resume/links/types.ts",
    "frontend/src/features/resume/export/shell.ts",
    "frontend/package.json",
]


def _yaml(path: str):
    return yaml.safe_load((ROOT / path).read_text())


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_only_pocketbase_shares_the_internal_network_with_the_materializer(compose_file):
    compose = _yaml(compose_file)
    assert compose["networks"]["materialize"] == {"internal": True}
    services = compose["services"]
    members = sorted(name for name, svc in services.items() if "materialize" in (svc.get("networks") or []))
    assert members == ["materializer", "pocketbase"]
    assert services["materializer"]["networks"] == ["materialize"]
    # PocketBase keeps the app network the runner and nginx reach it on.
    assert services["pocketbase"]["networks"] == ["default", "materialize"]


@pytest.mark.parametrize("compose_file", COMPOSE_FILES)
def test_the_materializer_runs_read_only_with_no_secret_port_or_privilege(compose_file):
    svc = _yaml(compose_file)["services"]["materializer"]
    assert svc["read_only"] is True
    assert svc["cap_drop"] == ["ALL"]
    assert svc["security_opt"] == ["no-new-privileges:true"]
    for key in ("environment", "env_file", "ports", "volumes", "privileged", "user"):
        assert key not in svc, (compose_file, key)


@pytest.mark.parametrize("compose_file", ["docker-compose.yml", "harness/compose.yml"])
def test_compose_builds_it_from_the_repository_root(compose_file):
    build = _yaml(compose_file)["services"]["materializer"]["build"]
    root = "." if compose_file == "docker-compose.yml" else ".."
    assert build == {"context": root, "dockerfile": "backend/materializer/Dockerfile"}


def test_the_image_matrix_builds_it_from_the_repository_root():
    workflow = _yaml(".github/workflows/publish-images.yml")
    (entry,) = [e for e in workflow["jobs"]["publish"]["strategy"]["matrix"]["include"] if e["service"] == "materializer"]
    assert entry == {
        "service": "materializer",
        "image": "materializer",
        "context": ".",
        "dockerfile": "./backend/materializer/Dockerfile",
    }


def test_the_ignore_file_admits_only_the_materializer_and_the_bundled_sources():
    lines = [ln for ln in (MATERIALIZER / "Dockerfile.dockerignore").read_text().splitlines() if ln and not ln.startswith("#")]
    assert lines[0] == "*"
    admitted = sorted(ln[1:] for ln in lines if ln.startswith("!"))
    assert admitted == sorted(["backend/materializer/", *BUNDLED])
    # Built output, local installs, and tests stay out even though their
    # directory is admitted.
    for kept_out in ("backend/materializer/node_modules", "backend/materializer/dist", "backend/materializer/test"):
        assert kept_out in lines and lines.index(kept_out) > lines.index("!backend/materializer/")


def test_the_dockerfile_copies_nothing_the_ignore_file_keeps_out():
    dockerfile = (MATERIALIZER / "Dockerfile").read_text()
    copied = []
    for line in dockerfile.splitlines():
        if line.startswith("COPY ") and "--from=" not in line:
            copied += line.split()[1:-1]
    assert copied, "no COPY lines"
    for path in copied:
        assert path.startswith("backend/materializer/") or path in BUNDLED, path
    for path in BUNDLED:
        assert path in copied, path
    # Runs as an unprivileged user, and the final image takes only the
    # bundle from the build stage.
    assert re.search(r"^USER 10001:10001$", dockerfile, re.M)
    assert dockerfile.count("COPY --from=build") == 1


def test_k8s_admits_only_pocketbase_pods_and_allows_no_egress():
    docs = [d for d in yaml.safe_load_all((ROOT / "k8s" / "materializer.yaml").read_text()) if d]
    by_kind = {d["kind"]: d for d in docs}
    assert sorted(by_kind) == ["Deployment", "NetworkPolicy", "Service"]
    policy = by_kind["NetworkPolicy"]["spec"]
    assert policy["podSelector"] == {"matchLabels": {"rounds.io/net": "materializer"}}
    assert policy["policyTypes"] == ["Ingress", "Egress"]
    assert policy["egress"] == []
    (rule,) = policy["ingress"]
    assert rule["from"] == [{"podSelector": {"matchLabels": {"rounds.io/net": "pocketbase"}}}]
    assert rule["ports"] == [{"protocol": "TCP", "port": 4100}]

    pod = by_kind["Deployment"]["spec"]["template"]
    assert pod["metadata"]["labels"]["rounds.io/net"] == "materializer"
    spec = pod["spec"]
    assert spec["automountServiceAccountToken"] is False
    assert spec["securityContext"]["runAsNonRoot"] is True
    (container,) = spec["containers"]
    assert container["securityContext"] == {
        "readOnlyRootFilesystem": True,
        "allowPrivilegeEscalation": False,
        "capabilities": {"drop": ["ALL"]},
    }
    assert "env" not in container and "envFrom" not in container and "volumeMounts" not in container


def test_pocketbase_pods_carry_the_label_the_policy_admits():
    docs = [d for d in yaml.safe_load_all((ROOT / "k8s" / "pocketbase.yaml").read_text()) if d]
    (deployment,) = [d for d in docs if d["kind"] == "Deployment"]
    assert deployment["spec"]["template"]["metadata"]["labels"]["rounds.io/net"] == "pocketbase"
    # The label is added to the pods only; the selector is unchanged.
    assert deployment["spec"]["selector"] == {"matchLabels": {"app": "pocketbase"}}
    assert "materializer.yaml" in _yaml("k8s/kustomization.yaml")["resources"]


def test_the_runner_image_leaves_the_materializer_out():
    lines = (ROOT / "backend" / ".dockerignore").read_text().splitlines()
    assert "materializer" in lines
