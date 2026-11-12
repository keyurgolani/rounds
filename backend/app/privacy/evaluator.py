"""Pure evaluators for the privacy policy (ROUNDS-14-L01, DR-0005).

They read the policy files beside this module, which
``node scripts/conformance/run.mjs --write`` copies from
``contracts/privacy/`` (TODO(ROUNDS-34-L08): the shared contracts package
takes the copy over). ``frontend/src/privacy/evaluator.ts`` answers the
same shared vectors the same way.

Every answer is a dict: ``{"decision": "deny", "code", "rule"}`` or
``{"decision": "allow", "obligations", "versions"}``. Nothing here reads
the environment, the clock, or the network, and nothing enforces: ROUNDS-14-L02
calls ``evaluate_egress`` at dispatch, and each row owner calls
``evaluate_sink`` and ``evaluate_retention`` at its sink.
"""
from __future__ import annotations

import ipaddress
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

HERE = Path(__file__).resolve().parent


def _load(name: str) -> Any:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


POLICY = _load("policy.json")
PURPOSES = _load("purposes.json")
FIELD_MAP = _load("field-map.json")
SECRET_PATTERNS = _load("secret-patterns.json")

VERSIONS = {v["id"]: f'{v["id"]}@{v["current"]}' for v in POLICY["versions"]}
_SINKS = {s["id"]: s for s in POLICY["sinks"]}
_CELLS = {(c["class"], c["sink"]): c for c in POLICY["matrix"]["cells"]}
_VIS_RULES = {(r["visibility"], r["sink"]): r for r in POLICY["visibilityRules"]}
_PURPOSES = {p["id"]: p for p in PURPOSES["purposes"]}
_ENTRIES = {e["id"]: e for e in FIELD_MAP["entries"]}
_LIFECYCLE = {r["id"]: r for r in POLICY["lifecycle"]["rows"] + POLICY["lifecycle"]["decided"]}
_LOC = POLICY["locations"]
_SYSTEM_FIELDS = ("id", "created", "updated")
_PATTERNS = [(p["id"], re.compile(p["regex"], re.ASCII)) for p in SECRET_PATTERNS["patterns"]]


def deny(code: str, rule: str) -> dict[str, Any]:
    return {"decision": "deny", "code": code, "rule": rule}


def allow(obligations: Iterable[str], versions: Sequence[str] = ("privacy", "consent", "redaction", "retention")) -> dict[str, Any]:
    return {"decision": "allow", "obligations": sorted(set(obligations)), "versions": {k: VERSIONS[k] for k in versions}}


# ---------------------------------------------------------------- field ids

def _split(field_id: str) -> tuple[str, str | None]:
    base, sep, pointer = field_id.partition("#")
    return base, (pointer if sep else None)


def _segments(pointer: str | None) -> list[str]:
    if not pointer:
        return []
    return [s.replace("~1", "/").replace("~0", "~") for s in pointer.split("/")[1:]]


def _pointer_match(pattern: list[str], segs: list[str]) -> bool:
    """A pattern covers ``segs`` when it is a prefix of them, ``*`` taking any one segment."""
    return len(pattern) <= len(segs) and all(p == "*" or p == s for p, s in zip(pattern, segs))


def _family_covers(wide: str, narrow: str) -> bool:
    return re.fullmatch(".*".join(re.escape(part) for part in wide.split("*")), narrow, re.S) is not None


def resolve_field(field_id: str) -> dict[str, Any] | None:
    """The field-map entry that classifies ``field_id``, or None. A JSON
    pointer takes its deepest covering entry (fewer wildcards first on a
    tie), then the column's own entry; ``pathsFrom`` reads another
    column's paths; a store's id, created, and updated take the store
    entry; a storage key takes the family that covers it."""
    if not isinstance(field_id, str) or not field_id:
        return None
    if field_id in _ENTRIES:
        return _ENTRIES[field_id]
    if field_id.startswith("storage:"):
        key = field_id[len("storage:"):]
        hits = [e for i, e in _ENTRIES.items() if i.startswith("storage:") and _family_covers(i[len("storage:"):], key)]
        return min(hits, key=lambda e: (e["id"].count("*"), -len(e["id"]))) if hits else None
    base, pointer = _split(field_id)
    if pointer is None:
        if base.startswith("pb:") and "." in base:
            store, _, name = base.partition(".")
            if name in _SYSTEM_FIELDS:
                return _ENTRIES.get(store)
        return None
    segs = _segments(pointer)
    for column in _columns(base):
        best = None
        for i, e in _ENTRIES.items():
            b, p = _split(i)
            if b != column or p is None:
                continue
            pattern = _segments(p)
            if _pointer_match(pattern, segs):
                rank = (len(pattern), -pattern.count("*"))
                if best is None or rank > best[0]:
                    best = (rank, e)
        if best:
            return best[1]
    return _ENTRIES.get(base)


def _columns(base: str) -> list[str]:
    out = [base]
    alias = _ENTRIES.get(base, {}).get("pathsFrom")
    if alias:
        out.append(alias)
    return out


def _family(entry: Mapping[str, Any]) -> tuple[str, str]:
    return ("class", entry["class"]) if "class" in entry else ("visibility", entry["visibility"])


# ---------------------------------------------------------------- sink rules

def _base_rule(entry: Mapping[str, Any], sink: str) -> tuple[dict[str, Any], str] | None:
    family, value = _family(entry)
    if family not in _SINKS[sink]["families"]:
        return None
    cell = _CELLS.get((value, sink)) if family == "class" else _VIS_RULES.get((value, sink))
    if not cell:
        return None
    return cell["rule"], ("matrix." if family == "class" else "visibility.") + cell["id"]


def _case_tighter(case: Mapping[str, Any], base: Mapping[str, Any]) -> bool:
    return all(case["when"].get(k) == v for k, v in base["when"].items()) and set(base["obligations"]) <= set(case["obligations"])


def tighter_or_equal(override: Mapping[str, Any], base: Mapping[str, Any]) -> bool:
    """True when ``override`` allows no more than ``base``: a deny always is;
    an allow keeps every obligation; a conditional allow keeps every
    condition and obligation of some base case; a consent allow keeps the
    same unit and obligations."""
    o, b = override["decision"], base["decision"]
    if o == "deny":
        return True
    if b == "deny":
        return False
    if o == "allow":
        return b == "allow" and set(base["obligations"]) <= set(override["obligations"])
    if o == "allow-if":
        if b == "allow":
            return all(set(base["obligations"]) <= set(c["obligations"]) for c in override["cases"])
        if b == "allow-if":
            return all(any(_case_tighter(c, bc) for bc in base["cases"]) for c in override["cases"])
        return False
    if o == "allow-with-consent":
        return b == "allow-with-consent" and override["consent"] == base["consent"] and set(base["obligations"]) <= set(override["obligations"])
    return False


def _with_overrides(entry: Mapping[str, Any], sink: str, rule: dict[str, Any], rule_id: str,
                    overrides: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any] | None, str, dict[str, Any] | None]:
    family, value = _family(entry)
    for o in overrides or ():
        if o.get("sink") != sink or o.get(family) != value:
            continue
        if not tighter_or_equal(o["rule"], rule):
            return None, rule_id, deny("OVERRIDE_RELAXES", f'override.{o.get("source", "unknown")}')
        rule, rule_id = o["rule"], f'override.{o.get("source", "unknown")}'
    return rule, rule_id, None


def _consent_ok(unit: str, consent: Mapping[str, Any], field_id: str, purpose: str | None) -> bool:
    if consent.get("unit") != "per-request" or consent.get("preview") is not True:
        return False
    if unit == "field-level":
        return field_id in (consent.get("fields") or [])
    if unit == "purpose-specific":
        return purpose is not None and consent.get("purpose") == purpose
    return unit == "per-request"


def _apply(rule: Mapping[str, Any], rule_id: str, entry: Mapping[str, Any], field_id: str,
           context: Mapping[str, Any]) -> dict[str, Any]:
    decision = rule["decision"]
    if decision == "deny":
        return deny(rule["code"], rule_id)
    if decision == "allow":
        return allow(rule["obligations"])
    if decision == "allow-if":
        for case in rule["cases"]:
            if all((entry["kind"] if k == "kind" else context.get(k)) == v for k, v in case["when"].items()):
                return allow(case["obligations"])
        return deny(rule["otherwise"], rule_id)
    if decision == "allow-with-consent":
        consent = context.get("consent") or {}
        purpose = context.get("purpose")
        if consent.get("unit") == "legacy-implicit":
            if context.get("purposeStatus") != "legacy":
                return deny("CONSENT_LEGACY_ONLY", "consent.legacy-implicit")
            kept = [o for o in rule["obligations"] if not o.startswith(("consent:", "preview:"))]
            return allow([*kept, "consent:legacy-implicit"])
        if _consent_ok(rule["consent"], consent, field_id, purpose):
            return allow(rule["obligations"])
        return deny(rule["otherwise"], rule_id)
    return deny("SINK_WITHOUT_RULE", rule_id)


def evaluate_sink(field_id: str, sink: str, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Whether ``field_id`` may reach ``sink``, and on what terms."""
    context = context or {}
    if sink not in _SINKS:
        return deny("SINK_WITHOUT_RULE", "sinks")
    entry = resolve_field(field_id)
    if entry is None:
        return deny("FIELD_UNCLASSIFIED", "field-map")
    base = _base_rule(entry, sink)
    if base is None:
        return deny("SINK_WITHOUT_RULE", f"sinks.{sink}")
    rule, rule_id, refused = _with_overrides(entry, sink, *base, context.get("overrides") or [])
    if refused:
        return refused
    return _apply(rule, rule_id, entry, field_id, context)


# ---------------------------------------------------------------- locations

def _ip(text: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(text.split("%", 1)[0])
    except ValueError:
        return None


def _unwrap(address: Any) -> Any:
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return address.ipv4_mapped
        if address.sixtofour is not None:
            return address.sixtofour
        if address in ipaddress.ip_network("64:ff9b::/96"):
            return ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
    return address


def _in(address: Any, nets: Iterable[str]) -> bool:
    for n in nets:
        net = ipaddress.ip_network(n, strict=False)
        if net.version == address.version and address in net:
            return True
    return False


_NEVER_NETS = _LOC["never"]["loopback"] + _LOC["never"]["linkLocal"] + _LOC["never"]["unspecified"] + _LOC["never"]["metadata"]


def _service_name(host: str) -> bool:
    host = host.rstrip(".").lower()
    if _ip(host) is not None:
        return False
    return "." not in host or host in _LOC["never"]["serviceNames"] or host.endswith(tuple(_LOC["never"]["serviceSuffixes"]))


def classify_destination(host: str, port: int, addresses: Sequence[str], settings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The location class of a destination, from its resolved addresses.
    ``settings`` carries ``gate`` (R0's private-network gate value) and
    ``allowlist`` (``ROUNDS_AI_PRIVATE_ENDPOINTS`` as written)."""
    settings = settings or {}
    host = str(host or "").strip("[]")
    if _service_name(host):
        return deny("DESTINATION_NEVER", "locations.never")
    found = [_ip(a) for a in addresses or []]
    if not found or any(a is None for a in found):
        return deny("DESTINATION_UNCLASSED", "locations")
    kinds = set()
    for a in map(_unwrap, found):
        if _in(a, _NEVER_NETS):
            return deny("DESTINATION_NEVER", "locations.never")
        if _in(a, _LOC["privateNetworks"]):
            kinds.add("private")
        elif _in(a, _LOC["nonPublic"]):
            return deny("DESTINATION_UNCLASSED", "locations")
        else:
            kinds.add("public")
    if kinds == {"private", "public"}:
        return deny("DESTINATION_MIXED", "locations")
    if kinds == {"public"}:
        return {"decision": "allow", "location": "third-party-hosted"}
    if settings.get("gate") != "enabled":
        return deny("DESTINATION_NOT_ALLOWLISTED", "locations.combination")
    entries = parse_private_endpoints(settings.get("allowlist") or "")
    for a in map(_unwrap, found):
        if not any(a.version == e["network"].version and a in e["network"] and int(port) == e["port"] for e in entries):
            return deny("DESTINATION_NOT_ALLOWLISTED", "locations.combination")
    return {"decision": "allow", "location": "operator-network"}


_ENTRY = re.compile(r"\A(?:\[(?P<v6>[^\]]+)\]|(?P<v4>[^:\[\]]+)):(?P<port>[0-9]{1,5})\Z")


def parse_private_endpoints(value: str) -> list[dict[str, Any]]:
    """``ROUNDS_AI_PRIVATE_ENDPOINTS`` as entries ``{"network", "port"}``.
    Raises ValueError naming the first entry it refuses."""
    name = "ROUNDS_AI_PRIVATE_ENDPOINTS"
    text = (value or "").strip()
    if not text:
        return []
    out = []
    for raw in text.split(","):
        item = raw.strip()
        if not item:
            raise ValueError(f"{name} has an empty entry; separate entries with single commas")
        m = _ENTRY.match(item)
        if not m:
            raise ValueError(f"{name} entry {item!r} isn't ip:port, [ipv6]:port, cidr:port, or [ipv6-cidr]:port")
        host = m.group("v6") or m.group("v4")
        port = int(m.group("port"))
        if not 1 <= port <= 65535:
            raise ValueError(f"{name} entry {item!r} has port {port}; ports run from 1 to 65535")
        try:
            if "%" in host or ("/" in host and not re.fullmatch(r"[0-9]{1,3}", host.split("/", 1)[1])):
                raise ValueError("a plain address and a prefix length, not a zone or a netmask")
            network = ipaddress.ip_network(host, strict=True)
        except ValueError:
            if _service_name(host) or not re.fullmatch(r"[0-9a-fA-F.:/]+", host.split("%", 1)[0]):
                raise ValueError(f"{name} entry {item!r} names a host; entries are addresses or CIDR ranges, and service names are never destinations") from None
            raise ValueError(f"{name} entry {item!r} isn't a valid address or CIDR range") from None
        if network.num_addresses == 1:
            network = ipaddress.ip_network(_unwrap(network.network_address))
        elif isinstance(network, ipaddress.IPv6Network) and network.subnet_of(ipaddress.ip_network("::ffff:0:0/96")):
            raise ValueError(f"{name} entry {item!r} is an IPv4-mapped range; write the IPv4 range")
        refused = [n for n in _NEVER_NETS if _overlaps(network, n)]
        if refused:
            raise ValueError(f"{name} entry {item!r} covers {refused[0]}, which is never a destination")
        if not any(_within(network, n) for n in _LOC["privateNetworks"]):
            raise ValueError(f"{name} entry {item!r} isn't inside a private network ({', '.join(_LOC['privateNetworks'])})")
        out.append({"network": network, "port": port})
    return out


def _overlaps(network: Any, other: str) -> bool:
    o = ipaddress.ip_network(other, strict=False)
    return network.version == o.version and network.overlaps(o)


def _within(network: Any, other: str) -> bool:
    o = ipaddress.ip_network(other, strict=False)
    return network.version == o.version and network.subnet_of(o)


# ---------------------------------------------------------------- egress

def _input_for(purpose: Mapping[str, Any], field_id: str) -> Mapping[str, Any] | None:
    """The deepest input entry that covers ``field_id``. An omitted path
    also holds for a column that reads its paths from that column."""
    base, pointer = _split(field_id)
    segs = _segments(pointer)
    aliases = _columns(base)[1:]
    best = None
    for item in purpose["inputs"]:
        ib, ip = _split(item["field"])
        if item["field"] == field_id:
            covers = True
        elif base.startswith("storage:"):
            covers = ib.startswith("storage:") and _family_covers(ib[len("storage:"):], base[len("storage:"):])
        elif ib == base or (item.get("omit") and ib in aliases):
            covers = (pointer is not None and _pointer_match(_segments(ip), segs)) if ip is not None else ib == base
        else:
            covers = False
        if covers:
            rank = (len(_segments(ip)), bool(item.get("omit")))
            if best is None or rank > best[0]:
                best = (rank, item)
    return best[1] if best else None


def evaluate_egress(purpose: str, field_ids: Sequence[str], endpoint: Mapping[str, Any] | None,
                    location: str | None, consent: Mapping[str, Any] | None,
                    context: Mapping[str, Any] | None = None,
                    registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Whether one provider request may go: ``purpose`` names a registered
    purpose, ``field_ids`` every classed value the payload carries as
    content, ``endpoint`` its host, port, resolved addresses, and
    credential, ``location`` the class the caller resolved, and
    ``consent`` what the user agreed to for this request. Flags such as
    ``ai_policy`` never stand in for consent. ``registry`` defaults to
    the purpose registry beside this module."""
    consent = consent or {}
    context = context or {}
    endpoint = endpoint or {}
    purposes = _PURPOSES if registry is None else {x["id"]: x for x in registry["purposes"]}
    p = purposes.get(purpose)
    if p is None:
        return deny("PURPOSE_UNREGISTERED", "purposes")
    rule = f"purposes.{purpose}"
    if p["status"] == "retired":
        return deny("PURPOSE_RETIRED", rule)
    cap = p.get("batchMax", 1)
    if int(consent.get("batch", 1) or 1) > cap:
        return deny("BATCH_OVER_CAP", f"{rule}.batchMax")
    entries = []
    for fid in field_ids:
        entry = resolve_field(fid)
        if entry is None:
            return deny("FIELD_UNCLASSIFIED", "field-map")
        if entry.get("class") == "Secret":
            return deny("SECRET_AS_CONTENT", "credentialChannel")
        item = _input_for(p, fid)
        if item is None:
            return deny("FIELD_NOT_ALLOWED", f"{rule}.inputs")
        if item.get("omit") and fid not in (consent.get("added") or []):
            return deny("FIELD_NOT_ADDED", f"{rule}.inputs")
        entries.append((fid, entry))
    credential = endpoint.get("credential")
    if credential:
        cred = resolve_field(credential.get("field", ""))
        if cred is None or cred.get("class") != "Secret":
            return deny("CREDENTIAL_NOT_SECRET", "credentialChannel")
        registered = credential.get("registeredFor") or {}
        if (str(registered.get("host", "")).lower(), int(registered.get("port") or 0)) != (str(endpoint.get("host", "")).lower(), int(endpoint.get("port") or 0)):
            return deny("CREDENTIAL_ENDPOINT_MISMATCH", "credentialChannel")
    if location not in {c["id"] for c in _LOC["classes"]}:
        return deny("DESTINATION_UNCLASSED", "locations")
    if endpoint.get("host") is not None:
        resolved = classify_destination(endpoint["host"], endpoint.get("port") or 0, endpoint.get("addresses") or [], endpoint.get("settings"))
        if resolved["decision"] == "deny":
            return resolved
        if resolved["location"] != location:
            return deny("LOCATION_MISMATCH", "locations")
    classed = [fid for fid, e in entries if "class" in e]
    unit = consent.get("unit")
    if unit == "legacy-implicit" and p["status"] != "legacy":
        return deny("CONSENT_LEGACY_ONLY", "consent.legacy-implicit")
    if classed and unit not in ("per-request", "legacy-implicit"):
        return deny("CONSENT_REQUIRED", "consent")
    obligations = [f"location:{location}"]
    sink_context = {"consent": consent, "purpose": purpose, "purposeStatus": p["status"], "purposeDeclares": True,
                    "overrides": context.get("overrides") or []}
    for fid, _entry in entries:
        answer = evaluate_sink(fid, "remote-ai", sink_context)
        if answer["decision"] == "deny":
            return answer
        obligations.extend(answer["obligations"])
    if p.get("toolAuthority") not in (None, "none"):
        obligations.append("tools:buffer-staged")
    if p.get("streaming"):
        obligations.append("stream:provisional-preview")
    if credential:
        obligations.append("credential:auth-header-only")
    if unit == "legacy-implicit":
        obligations.append("consent:legacy-implicit")
    return allow(obligations)


# ---------------------------------------------------------------- retention

def _instant(value: Any) -> datetime:
    """An instant; a timestamp without a zone reads as UTC."""
    if not isinstance(value, datetime):
        value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def evaluate_retention(row_id: str, value: Any, anchor: Any, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """When a ``row_id`` item expires and must be purged by, for the chosen
    ``value`` (None takes the row's default) from ``anchor``. ``context``
    may name the data's ``class`` and whether the account is a ``demo``."""
    context = context or {}
    row = _LIFECYCLE.get(row_id)
    if row is None:
        return deny("RETENTION_UNKNOWN_ROW", "lifecycle")
    rule = f"lifecycle.{row_id}"
    while "sameAs" in row:
        row = _LIFECYCLE[row["sameAs"]]
    spec = row["retention"]
    chosen = spec["default"] if value is None else value
    if isinstance(chosen, bool):
        return deny("OUT_OF_BOUNDS", rule)
    if "choices" in spec and chosen not in spec["choices"]:
        return deny("OUT_OF_BOUNDS", rule)
    if "range" in spec:
        lo, hi = spec["range"]
        if isinstance(chosen, bool) or not isinstance(chosen, int) or not lo <= chosen <= hi:
            return deny("OUT_OF_BOUNDS", rule)
    cls = context.get("class")
    if cls in row.get("neverClasses", []):
        return deny("NEVER_STORED", rule)
    if context.get("demo") and "demo" in row.get("neverFor", []):
        return deny("NEVER_STORED", rule)
    cap = row.get("maxDaysByClass", {}).get(cls)
    if cap is not None and isinstance(chosen, int) and chosen > cap:
        return deny("OUT_OF_BOUNDS", rule)
    start = _instant(anchor)
    out: dict[str, Any] = {"decision": "allow", "value": chosen, "versions": {"retention": VERSIONS["retention"]}}
    if chosen == "off":
        out.update({"stored": False, "expires_at": None, "purge_by": None})
        return out
    if chosen in ("until-delete", "pinned"):
        expires = None
    elif chosen == "delete":
        expires = start
    else:
        expires = start + timedelta(days=int(chosen))
    hours = row.get("purgeWithinHours", 24)
    out["expires_at"] = _iso(expires)
    out["purge_by"] = _iso(expires + timedelta(hours=hours)) if expires else None
    if expires and "warningDays" in row:
        out["warn_at"] = _iso(expires - timedelta(days=row["warningDays"]))
    if expires and "tombstoneDays" in row:
        out["tombstone_until"] = _iso(expires + timedelta(days=row["tombstoneDays"]))
    if "digestDays" in row:
        out["digest_until"] = _iso(start + timedelta(days=row["digestDays"]))
    renew = row.get("renewDays", {}).get(cls)
    if chosen == "pinned" and renew:
        out["renew_by"] = _iso(start + timedelta(days=renew))
    return out


def operator_setting(name: str) -> dict[str, Any]:
    """An operator setting's bounds and default, read from its lifecycle row."""
    for s in POLICY["operatorSettings"]:
        if s["name"] == name:
            if "row" not in s:
                return {"name": name, "default": s.get("default", "")}
            spec = _LIFECYCLE[s["row"]]["retention"]
            lo, hi = spec["range"]
            return {"name": name, "min": lo, "max": hi, "default": spec["default"], "row": s["row"]}
    raise KeyError(name)


# ---------------------------------------------------------------- secrets

def detect_secret(text: str) -> dict[str, Any] | None:
    """``{"code": "secret-detected", "findings": [{"pattern", "start", "end"}]}``
    with offsets in code points, or None. Never returns the match."""
    findings = []
    for pid, rx in _PATTERNS:
        for m in rx.finditer(text or ""):
            findings.append({"pattern": pid, "start": m.start(), "end": m.end()})
    if not findings:
        return None
    findings.sort(key=lambda f: (f["start"], f["end"], f["pattern"]))
    return {"code": "secret-detected", "findings": findings}
