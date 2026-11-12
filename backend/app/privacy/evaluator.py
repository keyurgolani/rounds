"""Pure evaluators for the privacy policy (ROUNDS-14-L01, DR-0005).

They read the policy files beside this module, which
``node scripts/conformance/run.mjs --write`` copies from
``contracts/privacy/`` (TODO(ROUNDS-34-L08): the shared contracts package
takes the copy over). ``frontend/src/privacy/evaluator.ts`` answers the
same shared vectors the same way.

Every answer is a dict: ``{"decision": "deny", "code", "rule"}`` or
``{"decision": "allow", "obligations", "versions"}``. A malformed argument
answers ``INPUT_INVALID`` with the rule naming it, never an exception.
Nothing here reads the environment, the clock, or the network, and
nothing enforces: ROUNDS-14-L02 calls ``evaluate_egress`` at dispatch, and
each row owner calls ``evaluate_sink`` and ``evaluate_retention`` at its
sink.
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
MAX_CODE_POINTS = SECRET_PATTERNS["maxCodePoints"]
# Context keys only evaluate_egress may set: it alone knows the purpose.
_TRUSTED = ("purposeStatus", "purposeDeclares")
_MISSING = object()


def deny(code: str, rule: str) -> dict[str, Any]:
    return {"decision": "deny", "code": code, "rule": rule}


def allow(obligations: Iterable[str], versions: Sequence[str] = ("privacy", "consent", "redaction", "retention")) -> dict[str, Any]:
    return {"decision": "allow", "obligations": sorted(set(obligations)), "versions": {k: VERSIONS[k] for k in versions}}


def _roles(registry: Mapping[str, Any]) -> frozenset[str]:
    """The provider roles a registered purpose may go through."""
    return frozenset(r["role"] for r in registry.get("roles", PURPOSES["roles"]) if r.get("purposes") != "none")


_ROLES = _roles(PURPOSES)


# ---------------------------------------------------------------- arguments
# Each check returns the dotted name of the first malformed argument, or
# None. Numbers read the way JSON reads in JavaScript, so 7.0 is the
# whole number 7 and true is never 1.

def _invalid(path: str) -> dict[str, Any]:
    return deny("INPUT_INVALID", f"input.{path}")


def _whole(x: Any) -> int | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return None


def _port(x: Any) -> bool:
    n = _whole(x)
    return n is not None and 1 <= n <= 65535


def _strings(x: Any) -> bool:
    return isinstance(x, (list, tuple)) and all(isinstance(s, str) for s in x)


def _optional(x: Mapping[str, Any], key: str, kind: type) -> bool:
    return x.get(key) is None or isinstance(x.get(key), kind)


def _rule_error(rule: Any) -> bool:
    if not isinstance(rule, Mapping):
        return True
    decision = rule.get("decision")
    if decision == "deny":
        return not isinstance(rule.get("code"), str)
    if decision == "allow":
        return not _strings(rule.get("obligations"))
    if decision == "allow-if":
        cases = rule.get("cases")
        return not (isinstance(cases, (list, tuple)) and isinstance(rule.get("otherwise"), str)
                    and all(isinstance(c, Mapping) and isinstance(c.get("when"), Mapping) and _strings(c.get("obligations")) for c in cases))
    if decision == "allow-with-consent":
        return not (isinstance(rule.get("consent"), str) and isinstance(rule.get("otherwise"), str) and _strings(rule.get("obligations")))
    return True


def _consent_error(consent: Any) -> str | None:
    if not isinstance(consent, Mapping):
        return "consent"
    for key in ("unit", "purpose"):
        if not _optional(consent, key, str):
            return f"consent.{key}"
    if not _optional(consent, "preview", bool):
        return "consent.preview"
    for key in ("fields", "added"):
        if consent.get(key) is not None and not _strings(consent[key]):
            return f"consent.{key}"
    if consent.get("batch") is not None and (_whole(consent["batch"]) or 0) < 1:
        return "consent.batch"
    return None


def _context_error(context: Any) -> str | None:
    if context is None:
        return None
    if not isinstance(context, Mapping):
        return "context"
    overrides = context.get("overrides")
    if overrides is not None:
        if not isinstance(overrides, (list, tuple)):
            return "context.overrides"
        for o in overrides:
            if (not isinstance(o, Mapping) or not isinstance(o.get("sink"), str) or _rule_error(o.get("rule"))
                    or not all(_optional(o, key, str) for key in ("source", "class", "visibility"))):
                return "context.overrides"
    if context.get("consent") is not None:
        err = _consent_error(context["consent"])
        if err:
            return f"context.{err}"
    return None


def _settings_error(settings: Any) -> str | None:
    if settings is None:
        return None
    if not isinstance(settings, Mapping):
        return "settings"
    for key in ("gate", "allowlist"):
        if not _optional(settings, key, str):
            return f"settings.{key}"
    return None


def _endpoint_error(endpoint: Any) -> str | None:
    if endpoint is None:
        return None
    if not isinstance(endpoint, Mapping):
        return "endpoint"
    for key in ("host", "role"):
        if not _optional(endpoint, key, str):
            return f"endpoint.{key}"
    if endpoint.get("port") is not None and not _port(endpoint["port"]):
        return "endpoint.port"
    if endpoint.get("host") and endpoint.get("port") is None:
        return "endpoint.port"
    if endpoint.get("addresses") is not None and not _strings(endpoint["addresses"]):
        return "endpoint.addresses"
    err = _settings_error(endpoint.get("settings"))
    if err:
        return f"endpoint.{err}"
    credential = endpoint.get("credential")
    if credential is None:
        return None
    if not isinstance(credential, Mapping):
        return "endpoint.credential"
    if not _optional(credential, "field", str):
        return "endpoint.credential.field"
    registered = credential.get("registeredFor")
    if registered is None:
        return None
    if not isinstance(registered, Mapping):
        return "endpoint.credential.registeredFor"
    if not _optional(registered, "host", str):
        return "endpoint.credential.registeredFor.host"
    if registered.get("port") is not None and not _port(registered["port"]):
        return "endpoint.credential.registeredFor.port"
    return None


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


_STORE = re.compile(r"\Apb:[a-z_][a-z0-9_]*\Z")


def descendants(field_id: str) -> list[str]:
    """The ids below ``field_id`` that the field map classes, in map order:
    a store's fields and their paths, a column's paths, or the deeper paths
    under a pointer, a ``*`` on either side matching any one segment. A
    path read through ``pathsFrom`` keeps the caller's column. Matches
    ``descendantsOf`` in scripts/conformance/lib/privacy/fields.mjs."""
    if not isinstance(field_id, str) or field_id.startswith("storage:"):
        return []
    out: list[str] = []
    seen: set[str] = set()

    def add(i: str) -> None:
        if i not in seen:
            seen.add(i)
            out.append(i)

    def alias_paths(column: str) -> None:
        alias = _ENTRIES.get(column, {}).get("pathsFrom")
        if alias:
            for i in _ENTRIES:
                b, p = _split(i)
                if p is not None and b == alias:
                    add(f"{column}#{p}")

    base, pointer = _split(field_id)
    if pointer is None:
        if _STORE.match(base):
            for i in _ENTRIES:
                if i.startswith(f"{base}."):
                    add(i)
            for i in _ENTRIES:
                if i.startswith(f"{base}.") and "#" not in i:
                    alias_paths(i)
            return out
        for i in _ENTRIES:
            b, p = _split(i)
            if p is not None and b == base:
                add(i)
        alias_paths(base)
        return out
    segs = _segments(pointer)

    def below(p: str) -> bool:
        pattern = _segments(p)
        return len(pattern) > len(segs) and all(s == "*" or q == "*" or q == s for s, q in zip(segs, pattern))

    for i in _ENTRIES:
        b, p = _split(i)
        if p is not None and b == base and below(p):
            add(i)
    alias = _ENTRIES.get(base, {}).get("pathsFrom")
    if alias:
        for i in _ENTRIES:
            b, p = _split(i)
            if p is not None and b == alias and below(p):
                add(f"{base}#{p}")
    return out


def _field_within(inner: str, outer: str) -> bool:
    """True when ``inner`` is ``outer`` or sits below it, by the same rule."""
    if inner == outer:
        return True
    ob, op = _split(outer)
    ib, ip = _split(inner)
    if op is None:
        if _STORE.match(ob):
            return inner.startswith(f"{ob}.")
        return ib == ob and ip is not None
    if ib != ob or ip is None:
        return False
    o, n = _segments(op), _segments(ip)
    return len(n) >= len(o) and all(s == "*" or t == "*" or t == s for s, t in zip(o, n))


def _family(entry: Mapping[str, Any]) -> tuple[str, str]:
    return ("class", entry["class"]) if "class" in entry else ("visibility", entry["visibility"])


# ---------------------------------------------------------------- sink rules

def _same(a: Any, b: Any) -> bool:
    """Equality without coercion: true is never 1, and an absent key matches nothing."""
    if a is _MISSING or b is _MISSING:
        return False
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, (str, type(None))) and type(a) is type(b):
        return a == b
    return False


def _base_rule(entry: Mapping[str, Any], sink: str) -> tuple[dict[str, Any], str] | None:
    family, value = _family(entry)
    if family not in _SINKS[sink]["families"]:
        return None
    cell = _CELLS.get((value, sink)) if family == "class" else _VIS_RULES.get((value, sink))
    if not cell:
        return None
    return cell["rule"], ("matrix." if family == "class" else "visibility.") + cell["id"]


def _case_tighter(case: Mapping[str, Any], base: Mapping[str, Any]) -> bool:
    return all(_same(case["when"].get(k, _MISSING), v) for k, v in base["when"].items()) and set(base["obligations"]) <= set(case["obligations"])


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
        source = "unknown" if o.get("source") is None else o["source"]
        if not tighter_or_equal(o["rule"], rule):
            return None, rule_id, deny("OVERRIDE_RELAXES", f"override.{source}")
        rule, rule_id = o["rule"], f"override.{source}"
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
            if all(_same(entry["kind"] if k == "kind" else context.get(k, _MISSING), v) for k, v in case["when"].items()):
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


def _entry_answer(entry: Mapping[str, Any], field_id: str, sink: str, context: Mapping[str, Any]) -> dict[str, Any]:
    base = _base_rule(entry, sink)
    if base is None:
        return deny("SINK_WITHOUT_RULE", f"sinks.{sink}")
    rule, rule_id, refused = _with_overrides(entry, sink, *base, context.get("overrides") or [])
    if refused:
        return refused
    return _apply(rule, rule_id, entry, field_id, context)


def _sink(field_id: str, sink: str, context: Mapping[str, Any], expand: bool = True) -> dict[str, Any]:
    if sink not in _SINKS:
        return deny("SINK_WITHOUT_RULE", "sinks")
    entry = resolve_field(field_id)
    if entry is None:
        return deny("FIELD_UNCLASSIFIED", "field-map")
    answer = _entry_answer(entry, field_id, sink, context)
    if answer["decision"] == "deny" or not expand:
        return answer
    obligations = list(answer["obligations"])
    for d in descendants(field_id):
        below = resolve_field(d)
        found = deny("FIELD_UNCLASSIFIED", "field-map") if below is None else _entry_answer(below, d, sink, context)
        if found["decision"] == "deny":
            return deny("FIELD_TOO_COARSE", f"field-map.{d}")
        obligations.extend(found["obligations"])
    return allow(obligations)


def evaluate_sink(field_id: str, sink: str, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Whether ``field_id`` may reach ``sink``, and on what terms. A parent
    id answers allow only when every entry below it allows the same sink in
    the same context; the first that doesn't is named in a
    ``FIELD_TOO_COARSE`` deny. Only ``evaluate_egress`` vouches for a
    purpose, so ``purposeStatus`` and ``purposeDeclares`` count for nothing
    here."""
    if not isinstance(field_id, str):
        return _invalid("field_id")
    if not isinstance(sink, str):
        return _invalid("sink")
    err = _context_error(context)
    if err:
        return _invalid(err)
    return _sink(field_id, sink, {k: v for k, v in (context or {}).items() if k not in _TRUSTED})


# ---------------------------------------------------------------- locations

def _ip(text: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(text.split("%", 1)[0])
    except ValueError:
        return None


_UNWRAP = [ipaddress.ip_network(n) for n in _LOC["unwrap"]]


def _unwrap(address: Any) -> Any:
    """The IPv4 address an IPv6 address carries right after one of the
    policy's unwrap prefixes, so it's judged as that IPv4 address."""
    if isinstance(address, ipaddress.IPv6Address):
        for net in _UNWRAP:
            if address in net:
                return ipaddress.IPv4Address((int(address) >> (96 - net.prefixlen)) & 0xFFFFFFFF)
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


def classify_destination(host: str, port: int, addresses: Sequence[str] | None,
                         settings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The location class of a destination, from its resolved addresses.
    ``settings`` carries ``gate`` (R0's private-network gate value) and
    ``allowlist`` (``ROUNDS_AI_PRIVATE_ENDPOINTS`` as written). An IP
    literal host must match every address."""
    if not isinstance(host, str):
        return _invalid("host")
    if not _port(port):
        return _invalid("port")
    if addresses is not None and not _strings(addresses):
        return _invalid("addresses")
    err = _settings_error(settings)
    if err:
        return _invalid(err)
    settings = settings or {}
    host = host.strip("[]")
    if _service_name(host):
        return deny("DESTINATION_NEVER", "locations.never")
    found = [_ip(a) for a in addresses or []]
    if not found or any(a is None for a in found):
        return deny("DESTINATION_UNCLASSED", "locations")
    literal = _ip(host)
    if literal is not None and any(_unwrap(a) != _unwrap(literal) for a in found):
        return deny("ADDRESS_MISMATCH", "locations")
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
    try:
        entries = parse_private_endpoints(settings.get("allowlist") or "")
    except ValueError:
        return deny("ALLOWLIST_INVALID", "locations.allowlistSetting")
    wanted = _whole(port)
    for a in map(_unwrap, found):
        if not any(a.version == e["network"].version and a in e["network"] and wanted == e["port"] for e in entries):
            return deny("DESTINATION_NOT_ALLOWLISTED", "locations.combination")
    return {"decision": "allow", "location": "operator-network"}


_ENTRY = re.compile(r"\A(?:\[(?P<v6>[^\]]+)\]|(?P<v4>[^:\[\]]+)):(?P<port>[0-9]{1,5})\Z")


def parse_private_endpoints(value: str | None) -> list[dict[str, Any]]:
    """``ROUNDS_AI_PRIVATE_ENDPOINTS`` as entries ``{"network", "port"}``.
    Raises ValueError naming the first entry it refuses by its position;
    the message shows an entry's network only once it has parsed as one."""
    name = "ROUNDS_AI_PRIVATE_ENDPOINTS"
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    text = (value or "").strip()
    if not text:
        return []
    out = []
    for n, raw in enumerate(text.split(","), start=1):
        item = raw.strip()
        entry = f"{name} entry {n}"
        if not item:
            raise ValueError(f"{entry} is empty; separate entries with single commas")
        m = _ENTRY.match(item)
        if not m:
            raise ValueError(f"{entry} isn't ip:port, [ipv6]:port, cidr:port, or [ipv6-cidr]:port")
        host = m.group("v6") or m.group("v4")
        if not 1 <= int(m.group("port")) <= 65535:
            raise ValueError(f"{entry} has a port outside 1 to 65535")
        port = int(m.group("port"))
        try:
            if "%" in host or ("/" in host and not re.fullmatch(r"[0-9]{1,3}", host.split("/", 1)[1])):
                raise ValueError("a plain address and a prefix length, not a zone or a netmask")
            network = ipaddress.ip_network(host, strict=True)
        except ValueError:
            if _service_name(host) or not re.fullmatch(r"[0-9a-fA-F.:/]+", host.split("%", 1)[0]):
                raise ValueError(f"{entry} names a host; entries are addresses or CIDR ranges, and service names are never destinations") from None
            raise ValueError(f"{entry} isn't a valid address or CIDR range") from None
        if network.num_addresses == 1:
            network = ipaddress.ip_network(_unwrap(network.network_address))
        elif isinstance(network, ipaddress.IPv6Network) and network.subnet_of(ipaddress.ip_network("::ffff:0:0/96")):
            raise ValueError(f"{entry} is an IPv4-mapped range; write the IPv4 range")
        refused = [x for x in _NEVER_NETS if _overlaps(network, x)]
        if refused:
            raise ValueError(f"{entry} ({network}) covers {refused[0]}, which is never a destination")
        if not any(_net_within(network, x) for x in _LOC["privateNetworks"]):
            raise ValueError(f"{entry} ({network}) isn't inside a private network ({', '.join(_LOC['privateNetworks'])})")
        out.append({"network": network, "port": port})
    return out


def _overlaps(network: Any, other: str) -> bool:
    o = ipaddress.ip_network(other, strict=False)
    return network.version == o.version and network.overlaps(o)


def _net_within(network: Any, other: str) -> bool:
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


def _below(purpose: Mapping[str, Any], field_id: str, rule: str) -> list[tuple[str, str]]:
    """What the input check reads below ``field_id``: the map's entries,
    then any omitted input the map doesn't hold, each with the rule a deny
    names."""
    out = [(d, f"field-map.{d}") for d in descendants(field_id)]
    seen = {d for d, _ in out}
    for item in purpose["inputs"]:
        f = item["field"]
        if item.get("omit") and f != field_id and f not in seen and _field_within(f, field_id):
            out.append((f, f"{rule}.inputs"))
    return out


def evaluate_egress(purpose: str, field_ids: Sequence[str], endpoint: Mapping[str, Any] | None,
                    location: str | None, consent: Mapping[str, Any] | None,
                    context: Mapping[str, Any] | None = None,
                    registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Whether one provider request may go: ``purpose`` names a registered
    purpose, ``field_ids`` every classed value the payload carries as
    content, ``endpoint`` the provider's ``role``, its host, port, resolved
    addresses, and credential, ``location`` the class the caller resolved,
    and ``consent`` what the user agreed to for this request. A field id
    covers everything below it, so each entry below must pass too. Flags
    such as ``ai_policy`` never stand in for consent. ``registry`` defaults
    to the purpose registry beside this module."""
    if not isinstance(purpose, str):
        return _invalid("purpose")
    if not isinstance(field_ids, (list, tuple)) or not _strings(field_ids):
        return _invalid("field_ids")
    if location is not None and not isinstance(location, str):
        return _invalid("location")
    err = (_consent_error(consent) if consent is not None else None) or _context_error(context) or _endpoint_error(endpoint)
    if err:
        return _invalid(err)
    consent = consent or {}
    context = context or {}
    endpoint = endpoint or {}
    if registry is None:
        purposes, roles = _PURPOSES, _ROLES
    else:
        purposes, roles = {x["id"]: x for x in registry["purposes"]}, _roles(registry)
    p = purposes.get(purpose)
    if p is None:
        return deny("PURPOSE_UNREGISTERED", "purposes")
    rule = f"purposes.{purpose}"
    if p["status"] == "retired":
        return deny("PURPOSE_RETIRED", rule)
    if endpoint.get("role") not in roles:
        return deny("ROLE_DENIED", "purposes.roles")
    batch = 1 if consent.get("batch") is None else _whole(consent["batch"])
    if batch > p.get("batchMax", 1):
        return deny("BATCH_OVER_CAP", f"{rule}.batchMax")
    added = consent.get("added") or []
    items: list[tuple[str, Mapping[str, Any], str | None]] = []
    for fid in field_ids:
        entry = resolve_field(fid)
        if entry is None:
            return deny("FIELD_UNCLASSIFIED", "field-map")
        if entry.get("class") == "Secret":
            return deny("SECRET_AS_CONTENT", "credentialChannel")
        item = _input_for(p, fid)
        if item is None:
            return deny("FIELD_NOT_ALLOWED", f"{rule}.inputs")
        if item.get("omit") and fid not in added:
            return deny("FIELD_NOT_ADDED", f"{rule}.inputs")
        items.append((fid, entry, None))
        for d, named in _below(p, fid, rule):
            below = resolve_field(d)
            covered = _input_for(p, d)
            if below is None or below.get("class") == "Secret" or covered is None or (covered.get("omit") and d not in added):
                return deny("FIELD_TOO_COARSE", named)
            items.append((d, below, named))
    host = endpoint.get("host") or None
    credential = endpoint.get("credential")
    if credential:
        cred = resolve_field(credential.get("field"))
        if cred is None or cred.get("class") != "Secret":
            return deny("CREDENTIAL_NOT_SECRET", "credentialChannel")
        registered = credential.get("registeredFor") or {}
        if (not registered.get("host") or registered.get("port") is None or host is None
                or (registered["host"].lower(), _whole(registered["port"])) != (host.lower(), _whole(endpoint["port"]))):
            return deny("CREDENTIAL_ENDPOINT_MISMATCH", "credentialChannel")
    if location not in {c["id"] for c in _LOC["classes"]}:
        return deny("DESTINATION_UNCLASSED", "locations")
    if host is None:
        if location != "this-server":
            return deny("DESTINATION_UNCLASSED", "locations")
    else:
        if not endpoint.get("addresses"):
            return deny("DESTINATION_UNCLASSED", "locations")
        resolved = classify_destination(host, endpoint["port"], endpoint["addresses"], endpoint.get("settings"))
        if resolved["decision"] == "deny":
            return resolved
        if resolved["location"] != location:
            return deny("LOCATION_MISMATCH", "locations")
    classed = [fid for fid, e, _ in items if "class" in e]
    unit = consent.get("unit")
    if unit == "legacy-implicit" and p["status"] != "legacy":
        return deny("CONSENT_LEGACY_ONLY", "consent.legacy-implicit")
    if classed and unit not in ("per-request", "legacy-implicit"):
        return deny("CONSENT_REQUIRED", "consent")
    obligations = [f"location:{location}"]
    trusted = {"consent": consent, "purpose": purpose, "purposeStatus": p["status"], "purposeDeclares": True,
               "overrides": context.get("overrides") or []}
    for fid, _entry, named in items:
        answer = _sink(fid, "remote-ai", trusted, expand=False)
        if answer["decision"] == "deny":
            return answer if named is None else deny("FIELD_TOO_COARSE", named)
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

# The ISO 8601 forms both evaluators read the same way. The day must exist
# in its month, and year 0 doesn't.
_ISO = re.compile(r"\A[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])"
                  r"(?:[T ](?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9](?:\.[0-9]{1,6})?)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])?)?\Z")


def _instant(value: Any) -> datetime | None:
    """An instant, or None; a timestamp without a zone reads as UTC."""
    try:
        if not isinstance(value, datetime):
            if not isinstance(value, str) or not _ISO.match(value):
                return None
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    v = value.astimezone(timezone.utc)
    return f"{v.year:04d}-{v.month:02d}-{v.day:02d}T{v.hour:02d}:{v.minute:02d}:{v.second:02d}Z"


def evaluate_retention(row_id: str, value: Any, anchor: Any, context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """When a ``row_id`` item expires and must be purged by, for the chosen
    ``value`` (None takes the row's default) from ``anchor``. ``context``
    may name the data's ``class`` and whether the account is a ``demo``."""
    if not isinstance(row_id, str):
        return _invalid("row_id")
    if context is not None and not isinstance(context, Mapping):
        return _invalid("context")
    context = context or {}
    if not _optional(context, "class", str):
        return _invalid("context.class")
    if not _optional(context, "demo", bool):
        return _invalid("context.demo")
    start = _instant(anchor)
    if start is None:
        return _invalid("anchor")
    row = _LIFECYCLE.get(row_id)
    if row is None:
        return deny("RETENTION_UNKNOWN_ROW", "lifecycle")
    rule = f"lifecycle.{row_id}"
    while "sameAs" in row:
        row = _LIFECYCLE[row["sameAs"]]
    spec = row["retention"]
    chosen = spec["default"] if value is None else value
    if isinstance(chosen, float) and _whole(chosen) is not None:
        chosen = _whole(chosen)
    if isinstance(chosen, bool):
        return deny("OUT_OF_BOUNDS", rule)
    if "choices" in spec and not any(_same(chosen, c) for c in spec["choices"]):
        return deny("OUT_OF_BOUNDS", rule)
    if "range" in spec:
        lo, hi = spec["range"]
        if not isinstance(chosen, int) or isinstance(chosen, bool) or not lo <= chosen <= hi:
            return deny("OUT_OF_BOUNDS", rule)
    cls = context.get("class")
    if cls in row.get("neverClasses", []):
        return deny("NEVER_STORED", rule)
    if context.get("demo") and "demo" in row.get("neverFor", []):
        return deny("NEVER_STORED", rule)
    cap = row.get("maxDaysByClass", {}).get(cls)
    if cap is not None and isinstance(chosen, int) and chosen > cap:
        return deny("OUT_OF_BOUNDS", rule)
    out: dict[str, Any] = {"decision": "allow", "value": chosen, "versions": {"retention": VERSIONS["retention"]}}
    if chosen == "off":
        out.update({"stored": False, "expires_at": None, "purge_by": None})
        return out
    try:
        _deadlines(out, row, chosen, start, cls)
    except OverflowError:
        return _invalid("anchor")
    return out


def _deadlines(out: dict[str, Any], row: Mapping[str, Any], chosen: Any, start: datetime, cls: Any) -> None:
    """Fill in the deadlines; raises OverflowError past year 9999."""
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

def detect_secret(text: str | None) -> dict[str, Any] | None:
    """``{"code": "secret-detected", "findings": [{"pattern", "start", "end"}]}``
    with offsets in code points, or None. Never returns the match. A text
    longer than ``maxCodePoints`` answers ``text-too-long`` unscanned, and
    a value that isn't text answers ``input-invalid``; either way the
    caller refuses it, as it would a secret."""
    if text is None:
        return None
    if not isinstance(text, str):
        return {"code": "input-invalid", "findings": []}
    if len(text) > MAX_CODE_POINTS:
        return {"code": "text-too-long", "findings": []}
    findings = []
    for pid, rx in _PATTERNS:
        for m in rx.finditer(text):
            findings.append({"pattern": pid, "start": m.start(), "end": m.end()})
    if not findings:
        return None
    findings.sort(key=lambda f: (f["start"], f["end"], f["pattern"]))
    return {"code": "secret-detected", "findings": findings}
