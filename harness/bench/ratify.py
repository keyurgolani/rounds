"""The ratification commit's edits for DR-0004@1 and DR-0002@2 (ROUNDS-02-L01).
Run it from the repository root once the lane's review names its round:

    python harness/bench/ratify.py <pr> <round> <YYYY-MM-DD>

It sets both records to ratified with the approver string
"rounds lane review (PR #<pr>, r<round>), <date>", pins each governed file's
SHA-256, regenerates the generated files, flips the committed-state
assertions in the two test files, and fails unless the pins are stable and
the conformance rules pass. Like the rest of harness/bench/, it ships
nowhere."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def pretty(value, indent: str = "", prefix: str = "", width: int = 140) -> str:
    """write_dr0004.py's layout; importing that script would count the tree again."""
    one = json.dumps(value, ensure_ascii=False)
    if value is None or not isinstance(value, (dict, list)) or len(indent) + len(prefix) + len(one) <= width:
        return one
    inner = indent + "  "
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[\n" + ",\n".join(inner + pretty(x, inner, "") for x in value) + "\n" + indent + "]"
    lines = [inner + json.dumps(k) + ": " + pretty(v, inner, json.dumps(k) + ": ") for k, v in value.items()]
    return "{\n" + ",\n".join(lines) + "\n" + indent + "}"


DR4 =ROOT / "docs/decisions/DR-0004-canonical-database.json"
DR2 = ROOT / "docs/decisions/DR-0002-authority-matrix.json"
# M4: DR-0004 pins the ERD's written part, the receipt, their schemas, and
# the ADR. The schema snapshot and the generated ERD are not governed.
GOV4 = ["contracts/database/erd-decisions.json", "contracts/database/erd-decisions.schema.json", "contracts/database/benchmark.json",
        "contracts/database/benchmark.schema.json", "docs/decisions/DR-0004-canonical-database.md"]
GOV2 = ["contracts/authority/matrix.json", "contracts/authority/packages.json", "contracts/authority/owner-labels.json",
        "contracts/authority/baseline-stores.json"]
TESTS = {"scripts/conformance/test/database-adr.test.mjs": "const STATUS = ", "scripts/conformance/test/authority.test.mjs": "const DR_STATUS = "}


def sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def node() -> str:
    mise = shutil.which("mise")
    if mise:
        found = subprocess.run([mise, "where", "node@22.23.3"], capture_output=True, text=True)
        if found.returncode == 0 and found.stdout.strip():
            return f"{found.stdout.strip()}/bin/node"
    return shutil.which("node") or "node"


def conformance(*args: str, check: bool) -> None:
    subprocess.run([node(), "scripts/conformance/run.mjs", "--base", "origin/next", *args], cwd=ROOT, check=check)


def set_dr4(pins: list[dict], approver: str, pr: int, date: str) -> None:
    r = json.loads(DR4.read_text())
    out = {}
    for k, v in r.items():
        out[k] = v
        if k == "approvalRef":
            out["ratifiedOn"] = date
    out.update({"status": "ratified", "approver": approver, "approvalRef": {"pr": pr, "governedFiles": pins}, "ratifiedOn": date})
    for d in out["decisions"]:
        d["status"] = "ratified"
    DR4.write_text(pretty(out) + "\n")


def set_dr2(pins: list[dict], approver: str, pr: int, date: str) -> None:
    text = DR2.read_text()
    d = json.loads(text)
    assert d["revision"] == 2, d["revision"]
    if d["status"] == "draft":
        # The record's own fields sit at two spaces; S1's status is deeper.
        for a, b in [('\n  "status": "draft",\n', '\n  "status": "ratified",\n'), ('\n  "approver": "",\n', f'\n  "approver": {json.dumps(approver)},\n')]:
            assert text.count(a) == 1, a
            text = text.replace(a, b, 1)
        ref = ",\n".join(f'      {{"path":{json.dumps(p["path"])},"sha256":"{p["sha256"]}"}}' for p in pins)
        old = '\n  "approvalRef": null,\n'
        assert text.count(old) == 1
        old = old[1:]
        text = text.replace(old, f'  "approvalRef": {{\n    "pr": {pr},\n    "governedFiles": [\n{ref}\n    ]\n  }},\n  "ratifiedOn": "{date}",\n', 1)
        s1 = text.index('"id": "S1"')
        at = text.index('"status": "draft"', s1)
        text = text[:at] + '"status": "ratified"' + text[at + len('"status": "draft"'):]
    else:
        for p in pins:
            old = next(g for g in d["approvalRef"]["governedFiles"] if g["path"] == p["path"])["sha256"]
            text = text.replace(old, p["sha256"])
    DR2.write_text(text)


def flip_tests() -> None:
    for rel, prefix in TESTS.items():
        p = ROOT / rel
        s = p.read_text()
        draft, ratified = f"{prefix}'draft';", f"{prefix}'ratified';"
        if ratified in s:
            continue
        assert s.count(draft) == 1, (rel, draft)
        p.write_text(s.replace(draft, ratified))


def pinned(record: Path) -> dict[str, str]:
    return {g["path"]: g["sha256"] for g in json.loads(record.read_text())["approvalRef"]["governedFiles"]}


def main(argv: list[str]) -> int:
    pr, rnd, date = int(argv[1]), argv[2], argv[3]
    approver = f"rounds lane review (PR #{pr}, r{rnd}), {date}"
    # Pass 1 pins placeholders so the ADR renders its ratified header; the
    # rules fail on the placeholders, which is expected here.
    set_dr4([{"path": p, "sha256": "0" * 64} for p in GOV4], approver, pr, date)
    set_dr2([{"path": p, "sha256": sha(p)} for p in GOV2], approver, pr, date)
    conformance("--write", check=False)
    # Pass 2 pins the real SHA-256s, which the ADR doesn't render, so the
    # regeneration changes nothing and the rules pass.
    set_dr4([{"path": p, "sha256": sha(p)} for p in GOV4], approver, pr, date)
    conformance("--write", check=True)
    bad = [p for p in GOV4 if sha(p) != pinned(DR4)[p]] + [p for p in GOV2 if sha(p) != pinned(DR2)[p]]
    if bad:
        print("unstable pins:", ", ".join(bad), file=sys.stderr)
        return 1
    flip_tests()
    conformance(check=True)
    print("approver:", approver)
    print("pinned:", len(GOV4), "for DR-0004 and", len(GOV2), "for DR-0002; now run node --test scripts/conformance")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
