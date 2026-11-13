"""The move of saved AI provider keys and model lists (ROUNDS-14-L02 stage A).

Runs 1700008800_ai_credentials.js and 1700008820_ai_credentials_move.js on
node's SQLite (ai_credentials_move_runner.cjs), with PocketBase's column
shapes and 1700008800's own indexes and owner triggers: the move of each
saved key as legacy-v0, a pair under two accounts marked suspect-planted,
a first-party kind with its own address made compatible, the model list
seeded with each saved model choice, the old key columns cleared, the dry
run that changes nothing and reports what the apply logs, and a down step
that puts every moved pair and kind back. Static checks hold the manifest,
the allowlist entry, and the runbook to the migration. The harness runs
the same migrations on a real PocketBase."""
from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MIGRATIONS = ROOT / "pocketbase" / "pb_migrations"
RUNNER = HERE / "ai_credentials_move_runner.cjs"
CREATE = "1700008800_ai_credentials.js"
MOVE = "1700008820_ai_credentials_move.js"
MANIFEST = ROOT / "pocketbase" / "migration-manifests" / "ai-credentials-v1.json"
ALLOWLIST = ROOT / "scripts" / "migration-lint-allowlist.json"

UA, UB, UC = "usera0000000001", "userb0000000001", "userc0000000001"


def pair(n: int) -> tuple[str, str]:
    return (base64.b64encode(f"legacy-ciphertext-{n:04d}-padding".encode()).decode(),
            base64.b64encode(bytes([n]) * 12).decode())


K1, K2, K3 = pair(1), pair(2), pair(3)


def provider(pid, user, kind, key=("", ""), base_url="", models=None):
    return {"id": pid, "user": user, "kind": kind, "label": pid, "base_url": base_url, "encrypted_key": key[0],
            "key_iv": key[1], "models_cache": None if models is None else json.dumps(models)}


PROVIDERS = [
    # A first-party provider with its key and a cached list.
    provider("pa1000000000001", UA, "openai", K1, models=["gpt-b", "gpt-a", "gpt-a", 7, "bad\nname", "x" * 257]),
    # A first-party kind with an address of its own.
    provider("pa2000000000001", UA, "anthropic", K2, "https://llm.example.test/v1", ["claude-x"]),
    # A compatible provider whose key was copied onto another account's.
    provider("pb1000000000001", UB, "openai-compatible", K3, "https://b.example.test/v1", ["local"]),
    provider("pc1000000000001", UC, "openai-compatible", K3, "https://c.example.test/v1"),
    # No key, and a key with one half.
    provider("pa3000000000001", UA, "anthropic"),
    provider("pa4000000000001", UA, "openai", (K1[0], "")),
]
SETTINGS = [
    {"id": "sa0000000000001", "user": UA, "text_provider": "pa1000000000001", "text_model": "gpt-typed",
     "vision_provider": "pa2000000000001", "vision_model": "claude-x"},
    {"id": "sb0000000000001", "user": UB, "text_provider": "pb1000000000001", "text_model": "local",
     "vision_provider": "", "vision_model": ""},
]


def seed_steps() -> list[dict]:
    return [
        {"op": "seed", "table": "users", "rows": [{"id": u} for u in (UA, UB, UC)]},
        {"op": "seed", "table": "ai_providers", "rows": PROVIDERS},
        {"op": "seed", "table": "ai_settings", "rows": SETTINGS},
        {"op": "up", "file": CREATE},
    ]


def run(steps: list[dict], env: dict | None = None) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the migration checks; CI installs it"
    res = subprocess.run([node, str(RUNNER), str(MIGRATIONS)], input=json.dumps({"env": env or {}, "steps": steps}),
                         capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    for r in out["results"][: len(seed_steps())]:
        assert r.get("ok", True), r
    return out


def moved() -> dict:
    out = run([*seed_steps(), {"op": "up", "file": MOVE}, {"op": "dump"}])
    assert out["results"][-2] == {"ok": True}, out["results"][-2]
    return out


def by_provider(rows):
    return {r["provider"]: r for r in rows}


# ---- the move -----------------------------------------------------------------


def test_each_saved_key_moves_as_it_was_and_the_old_columns_clear():
    out = moved()
    dump = out["results"][-1]
    creds = by_provider(dump["ai_credentials"])
    assert set(creds) == {"pa1000000000001", "pa2000000000001", "pb1000000000001", "pc1000000000001"}
    one = creds["pa1000000000001"]
    assert (one["user"], one["wrap"], one["key_version"], one["ciphertext"], one["nonce"]) == (UA, "legacy-v0", 1, *K1)
    assert (one["legacy_ciphertext"], one["legacy_nonce"]) == K1
    # A moved key names no address until the runner rewraps it.
    assert (one["registered_host"], one["registered_port"], one["status"]) == ("", 0, "active")
    halves = {r["id"]: (r["encrypted_key"], r["key_iv"]) for r in dump["ai_providers"]}
    # One half alone was never a key, so it stays as it was.
    assert halves.pop("pa4000000000001") == (K1[0], "")
    assert set(halves.values()) == {("", "")}
    # The cached lists stay where they were.
    cache = {r["id"]: r["models_cache"] for r in dump["ai_providers"]}
    assert cache == {p["id"]: p["models_cache"] for p in PROVIDERS}


def test_a_pair_under_two_accounts_is_suspect_on_both():
    creds = by_provider(moved()["results"][-1]["ai_credentials"])
    assert creds["pb1000000000001"]["status"] == creds["pc1000000000001"]["status"] == "suspect-planted"
    assert creds["pa1000000000001"]["status"] == creds["pa2000000000001"]["status"] == "active"


def test_a_first_party_kind_with_its_own_address_becomes_compatible():
    dump = moved()["results"][-1]
    kinds = {r["id"]: r["kind"] for r in dump["ai_providers"]}
    assert kinds["pa2000000000001"] == "anthropic-compatible"
    assert kinds["pa1000000000001"] == "openai" and kinds["pb1000000000001"] == "openai-compatible"
    (param,) = dump["_params"]
    assert param["key"] == MOVE
    assert json.loads(param["value"]) == {"migration": MOVE[:-3], "kinds": [{"provider": "pa2000000000001",
                                                                             "kind": "anthropic"}]}


def test_the_model_lists_seed_from_the_cache_and_the_saved_choices():
    rows = moved()["results"][-1]["ai_provider_models"]
    got = sorted((r["provider"], r["model"], r["verification"], r["user"]) for r in rows)
    assert got == [
        ("pa1000000000001", "gpt-a", "registry", UA),
        ("pa1000000000001", "gpt-b", "registry", UA),
        ("pa1000000000001", "gpt-typed", "user-declared", UA),
        ("pa2000000000001", "claude-x", "user-declared", UA),
        ("pb1000000000001", "local", "user-declared", UB),
    ]


def test_the_apply_logs_its_counts_and_checksum_and_no_key():
    out = moved()
    (line,) = [json.loads(l) for l in out["logs"] if "ai_credentials_moved" in l]
    assert line == {"v": "obs/v1", "event": "ai_credentials_moved", "service": "pocketbase",
                    "checksum": line["checksum"], "providers": 6, "keys_moved": 4, "keys_suspect_planted": 2,
                    "halves_left": 1, "kinds_converted": 1, "providers_with_models": 3, "models_seeded": 2,
                    "models_declared": 3}
    assert line["checksum"].startswith("sha256:") and len(line["checksum"]) == 71
    text = "\n".join(out["logs"])
    for key in (K1, K2, K3):
        assert key[0] not in text and key[1] not in text


def test_the_owner_triggers_hold_every_moved_row_to_its_providers_account():
    out = run([*seed_steps(), {"op": "up", "file": MOVE},
               {"op": "sql", "sql": "UPDATE ai_providers SET user = 'userb0000000001' WHERE id = 'pa1000000000001'"},
               {"op": "sql", "sql": "INSERT INTO ai_provider_models (id, user, provider, model, verification) "
                                    "VALUES ('m00000000000001', 'userb0000000001', 'pa1000000000001', 'x', 'registry')"}])
    moving, planting = out["results"][-2:]
    assert not moving["ok"] and "relation endpoint denied" in moving["error"]
    assert not planting["ok"] and "relation endpoint denied" in planting["error"]


# ---- the dry run ------------------------------------------------------------------

DRY = {"ROUNDS_AI_CREDENTIALS_MOVE": "dry-run", "ROUNDS_AI_CREDENTIALS_MOVE_REPORT": "/tmp/reports/ai-move.json"}


def test_a_dry_run_changes_nothing_and_reports_what_the_apply_logs():
    dry = run([*seed_steps(), {"op": "dump"}, {"op": "up", "file": MOVE}, {"op": "dump"}], DRY)
    before, result, after = dry["results"][-3:]
    assert not result["ok"] and "dry run complete" in result["error"]
    assert after == before
    (report,) = dry["written"]
    assert report["path"] == DRY["ROUNDS_AI_CREDENTIALS_MOVE_REPORT"] and report["perm"] == 0o600
    body = json.loads(report["data"])
    applied = [json.loads(l) for l in moved()["logs"] if "ai_credentials_moved" in l][0]
    assert body["status"] == "ok" and body["dry_run"] is True
    assert body["checksum"] == applied["checksum"]
    assert body["counts"] == {k: v for k, v in applied.items() if k not in ("v", "event", "service", "checksum")}
    for key in (K1, K2, K3):
        assert key[0] not in report["data"] and key[1] not in report["data"]


@pytest.mark.parametrize("report", ["", "/srv/pb_data/ai-move.json"])
def test_a_dry_run_needs_a_report_path_outside_pb_data(report):
    out = run([*seed_steps(), {"op": "up", "file": MOVE}, {"op": "dump"}],
              {"ROUNDS_AI_CREDENTIALS_MOVE": "dry-run", "ROUNDS_AI_CREDENTIALS_MOVE_REPORT": report})
    result, dump = out["results"][-2:]
    assert not result["ok"]
    assert ("needs ROUNDS_AI_CREDENTIALS_MOVE_REPORT" if not report else "inside pb_data") in result["error"]
    assert dump["ai_credentials"] == [] and out["written"] == []


# ---- down ----------------------------------------------------------------------


def test_down_puts_every_moved_pair_and_kind_back():
    out = run([*seed_steps(), {"op": "dump"}, {"op": "up", "file": MOVE}, {"op": "down", "file": MOVE},
               {"op": "dump"}, {"op": "down", "file": CREATE}, {"op": "dump"}])
    before, _up, down, after, drop, dropped = out["results"][-6:]
    assert down == {"ok": True} and drop == {"ok": True}
    keep = ("id", "user", "kind", "base_url", "encrypted_key", "key_iv", "models_cache")
    strip = lambda rows: [{k: r[k] for k in keep} for r in rows]  # noqa: E731
    assert strip(after["ai_providers"]) == strip(before["ai_providers"])
    assert after["ai_credentials"] == [] and after["ai_provider_models"] == [] and after["_params"] == []
    assert dropped["ai_credentials"] is None and dropped["ai_provider_models"] is None


def test_down_after_a_rewrap_puts_the_moved_pair_back():
    new_ct = base64.b64encode(b"rewrapped-ciphertext-under-aad-v1").decode()
    out = run([*seed_steps(), {"op": "up", "file": MOVE},
               {"op": "sql", "sql": "UPDATE ai_credentials SET wrap = 'aad-v1', ciphertext = '%s', "
                                    "registered_host = 'api.openai.com', registered_port = 443 "
                                    "WHERE provider = 'pa1000000000001'" % new_ct},
               {"op": "down", "file": MOVE}, {"op": "dump"}])
    providers = {r["id"]: r for r in out["results"][-1]["ai_providers"]}
    assert (providers["pa1000000000001"]["encrypted_key"], providers["pa1000000000001"]["key_iv"]) == K1


def test_a_key_entered_after_the_upgrade_is_gone_after_a_rollback():
    out = run([*seed_steps(), {"op": "up", "file": MOVE},
               {"op": "sql", "sql": "UPDATE ai_credentials SET wrap = 'aad-v1', legacy_ciphertext = '', "
                                    "legacy_nonce = '' WHERE provider = 'pa1000000000001'"},
               {"op": "down", "file": MOVE}, {"op": "dump"}])
    providers = {r["id"]: r for r in out["results"][-1]["ai_providers"]}
    assert (providers["pa1000000000001"]["encrypted_key"], providers["pa1000000000001"]["key_iv"]) == ("", "")
    assert out["results"][-1]["ai_credentials"] == []


def test_down_keeps_a_kind_changed_again_since():
    out = run([*seed_steps(), {"op": "up", "file": MOVE},
               {"op": "sql", "sql": "UPDATE ai_providers SET kind = 'openai-compatible' WHERE id = 'pa2000000000001'"},
               {"op": "down", "file": MOVE}, {"op": "dump"}])
    kinds = {r["id"]: r["kind"] for r in out["results"][-1]["ai_providers"]}
    assert kinds["pa2000000000001"] == "openai-compatible"


def test_the_collections_stay_while_they_hold_rows():
    out = run([*seed_steps(), {"op": "up", "file": MOVE}, {"op": "down", "file": CREATE}, {"op": "dump"}])
    refused, dump = out["results"][-2:]
    assert not refused["ok"] and "still holds rows" in refused["error"]
    assert len(dump["ai_credentials"]) == 4


# ---- decisions -------------------------------------------------------------------

DECIDE = r"""
const [migrationPath, argsJson] = process.argv.slice(2);
globalThis.migrate = () => {};
const m = require(migrationPath);
const args = JSON.parse(argsJson);
process.stdout.write(JSON.stringify(args.map((a) => m.cachedModels(a))));
"""


def test_a_cached_list_keeps_only_model_names_once_and_at_most_a_thousand(tmp_path):
    node = shutil.which("node")
    script = tmp_path / "decide.cjs"
    script.write_text(DECIDE)
    cases = ["", "not json", json.dumps({"a": 1}), json.dumps(["b", "a", "b", "", None, "tab\tx", "y" * 256, "y" * 257]),
             json.dumps(["m%04d" % i for i in range(1200)])]
    res = subprocess.run([node, str(script), str(MIGRATIONS / MOVE), json.dumps(cases)], capture_output=True, text=True,
                         timeout=60)
    assert res.returncode == 0, res.stderr
    empty, bad, obj, mixed, many = json.loads(res.stdout)
    assert empty == bad == obj == []
    assert mixed == ["a", "b", "y" * 256]
    assert many == ["m%04d" % i for i in range(1000)]


# ---- the manifest, the allowlist, and the runbook ---------------------------------------


def test_the_manifest_names_what_the_migration_writes():
    manifest = json.loads(MANIFEST.read_text())
    src = (MIGRATIONS / MOVE).read_text()
    assert manifest["manifest"] == "ai-credentials-v1" and manifest["migration"] == MOVE[:-3]
    assert manifest["dry_run"]["mode_env"] == "ROUNDS_AI_CREDENTIALS_MOVE" in src
    assert manifest["dry_run"]["report_env"] == "ROUNDS_AI_CREDENTIALS_MOVE_REPORT" in src
    assert manifest["journal"]["param"] == MOVE
    assert set(manifest["report"]["counts"]) == {"providers", "keys_moved", "keys_suspect_planted", "halves_left",
                                                 "kinds_converted", "providers_with_models", "models_seeded",
                                                 "models_declared"}
    assert set(manifest["collections"]) == {"ai_providers", "ai_credentials", "ai_provider_models", "ai_settings"}


def test_the_allowlist_entry_pins_this_migration_for_its_row_writes():
    entries = [e for e in json.loads(ALLOWLIST.read_text())["entries"] if e["path"].endswith(MOVE)]
    (entry,) = entries
    assert entry["rules"] == ["rewrites-rows"] and entry["issue"] == "#73"
    assert entry["manifest"] == "pocketbase/migration-manifests/ai-credentials-v1.json"
    assert entry["sha256"] == hashlib.sha256((MIGRATIONS / MOVE).read_bytes()).hexdigest()


def test_the_runbook_covers_the_dry_run_the_rewrap_and_the_rollback():
    ops = (ROOT / "docs" / "operations.md").read_text()
    section = ops[ops.index("\n### AI provider keys\n") + 1:]
    section = section[: section.index("\n## ")]
    for needle in ("ROUNDS_AI_CREDENTIALS_MOVE=dry-run", "ROUNDS_AI_CREDENTIALS_MOVE_REPORT", "migrate down 3",
                   "ai_credentials_moved", "keyring_unavailable"):
        assert needle in section, needle
