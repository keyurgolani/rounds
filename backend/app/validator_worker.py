"""The validator process (ROUNDS-00A-L02).

``app.validators`` starts this file as ``python3 -I -S`` with an empty
environment, in every gate state, so a validator predicate never runs in
the API process. It reads one JSON request on stdin:

    {"checks": [{"code": "lambda inp, out: ...", "input": ..., "output": ...}]}

and writes one JSON line on stdout: ``{"results": [[passed, error], ...]}``,
in order. ``error`` is null unless the predicate couldn't run.

Each predicate gets only the builtins below. The caller bounds the time
and the output; it imports nothing but the standard library's json and
sys, so it doesn't depend on the runner's code or packages.

TODO(ROUNDS-00A-L05): #5 moves this process into the code worker.
"""
import json
import sys

SAFE_BUILTINS = {
    "len": len, "range": range, "sum": sum, "set": set, "sorted": sorted,
    "all": all, "any": any, "abs": abs, "min": min, "max": max,
    "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
    "isinstance": isinstance,
    "list": list, "tuple": tuple, "dict": dict, "str": str,
    "int": int, "float": float, "bool": bool,
    "True": True, "False": False, "None": None,
}


def check(code, inp, out):
    if not isinstance(code, str):
        return [False, "Validator error: missing 'code' string"]
    try:
        predicate = eval(code, {"__builtins__": dict(SAFE_BUILTINS)}, {})
    except Exception as e:  # noqa: BLE001
        return [False, f"Validator error: {e}"]
    try:
        return [bool(predicate(inp, out)), None]
    except Exception as e:  # noqa: BLE001
        return [False, f"Validator error: {e}"]


def main():
    request = json.loads(sys.stdin.read())
    results = [check(c.get("code"), c.get("input"), c.get("output")) for c in request["checks"]]
    sys.stdout.write(json.dumps({"results": results}))


if __name__ == "__main__":
    main()
