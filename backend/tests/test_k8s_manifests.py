"""Kubernetes manifest guarantees (ROUNDS-00A-L01).

Candidate code runs inside the runner pod until #5's workers, so no pod
gets a credential it doesn't use."""
from pathlib import Path

import yaml

K8S = Path(__file__).resolve().parents[2] / "k8s"


def _pod_specs() -> dict[str, dict]:
    specs = {}
    # The base's manifests and the overlays' (k8s/overlays/*/), so an
    # opt-in Deployment is held to the same rules.
    for manifest in sorted([*K8S.glob("*.yaml"), *K8S.glob("overlays/*/*.yaml")]):
        for doc in yaml.safe_load_all(manifest.read_text()):
            if doc and doc.get("kind") == "Deployment":
                specs[manifest.name] = doc["spec"]["template"]["spec"]
    return specs


def test_no_pod_mounts_a_service_account_token():
    specs = _pod_specs()
    assert set(specs) == {"runner.yaml", "pocketbase.yaml", "frontend.yaml", "materializer.yaml"}
    for name, spec in specs.items():
        assert spec.get("automountServiceAccountToken") is False, name
