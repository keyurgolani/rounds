/// <reference path="../pb_data/types.d.ts" />

const ASSIGNMENTS = [
  {
    "slug": "csv-summarize-py",
    "title": "CSV Summarizer",
    "difficulty": "easy",
    "language": "python",
    "time_budget_min": 45,
    "ai_policy": "off",
    "entrypoint": "python3 harness/run.py",
    "prompt_md": "# CSV Summarizer\n\nImplement `summarize(csv_path, out_path)` in `summarize.py`.\n\n## Contract\n\nRead a CSV file at `csv_path`. The file has two columns:\n\n```csv\nname,score\nAlice,87\nBob,92\nCarol,71\n```\n\nWrite a JSON file to `out_path`:\n\n```json\n{\"count\": 3, \"mean_score\": 83.33, \"max\": {\"name\": \"Bob\", \"score\": 92}, \"min\": {\"name\": \"Carol\", \"score\": 71}}\n```\n\nFor an **empty** CSV (header row only, no data), the output is exactly:\n\n```json\n{\"count\": 0}\n```\n\n(no other keys.)\n\n## Constraints\n\n- Use Python's standard library only (`csv`, `json`).\n- Names may contain spaces; CSV quoting follows the default `csv` module dialect.\n- The score column is integer-valued.\n- Mean precision: use float; the harness allows up to 0.001 absolute error.\n\n## Deliverables\n\n- `summarize.py` implementing the function.\n- Optional: `NOTES.md` with any trade-off you made (e.g., one-pass vs two-pass, how you handled malformed rows).\n\n## Time budget\n\n~45 minutes.\n",
    "starter_files": [
      {
        "path": "NOTES.md",
        "contents": "# Notes\n\nUse this file to record design decisions or trade-offs the reviewer should know about.\n"
      },
      {
        "path": "summarize.py",
        "contents": "\"\"\"CSV Summarizer \u2014 implement summarize().\"\"\"\nfrom __future__ import annotations\n\n\ndef summarize(csv_path: str, out_path: str) -> None:\n    \"\"\"Read csv_path, compute stats, write JSON to out_path.\n\n    See prompt.md for the contract.\n    \"\"\"\n    raise NotImplementedError\n"
      }
    ],
    "harness_files": [
      {
        "path": "harness/run.py",
        "contents": "\"\"\"Grading harness for csv-summarize-py.\n\nCreates fixture CSVs in a tempdir, calls the candidate's summarize(),\nreads the output, asserts shape + values. Emits one JSON line on\nstdout matching the take-home runner contract.\"\"\"\nfrom __future__ import annotations\n\nimport json\nimport os\nimport sys\nimport tempfile\nimport time\nimport traceback\nfrom typing import Any\n\n\ndef _safe_call_summarize(csv_path: str, out_path: str) -> str:\n    \"\"\"Returns \"\" on success, or the error trace string on failure.\"\"\"\n    try:\n        from summarize import summarize\n    except Exception:\n        return f\"couldn't import summarize: {traceback.format_exc()[:500]}\"\n    try:\n        summarize(csv_path, out_path)\n        return \"\"\n    except Exception:\n        return f\"summarize raised: {traceback.format_exc()[:500]}\"\n\n\ndef _read_json(path: str) -> dict[str, Any] | None:\n    try:\n        with open(path, encoding=\"utf-8\") as f:\n            return json.load(f)\n    except Exception:\n        return None\n\n\ndef _write_csv(path: str, rows: list[tuple[str, int]]) -> None:\n    with open(path, \"w\", encoding=\"utf-8\") as f:\n        f.write(\"name,score\\n\")\n        for name, score in rows:\n            f.write(f\"{name},{score}\\n\")\n\n\ndef _populated_run() -> dict[str, Any] | None:\n    \"\"\"Run summarize against a 3-row fixture and return the parsed\n    output (or None on failure). Memoized in module-level state so\n    multiple criteria don't re-run the candidate's code.\"\"\"\n    if hasattr(_populated_run, \"_cache\"):\n        return _populated_run._cache  # type: ignore[attr-defined]\n    tmp = tempfile.mkdtemp(prefix=\"csv-harness-\")\n    csv_path = os.path.join(tmp, \"in.csv\")\n    out_path = os.path.join(tmp, \"out.json\")\n    _write_csv(csv_path, [(\"Alice\", 87), (\"Bob\", 92), (\"Carol\", 71)])\n    err = _safe_call_summarize(csv_path, out_path)\n    if err:\n        _populated_run._cache = {\"_error\": err}  # type: ignore[attr-defined]\n        return _populated_run._cache  # type: ignore[attr-defined]\n    out = _read_json(out_path)\n    if out is None:\n        _populated_run._cache = {\"_error\": f\"output file not valid JSON at {out_path}\"}  # type: ignore[attr-defined]\n    else:\n        _populated_run._cache = out  # type: ignore[attr-defined]\n    return _populated_run._cache  # type: ignore[attr-defined]\n\n\ndef _empty_run() -> dict[str, Any] | None:\n    if hasattr(_empty_run, \"_cache\"):\n        return _empty_run._cache  # type: ignore[attr-defined]\n    tmp = tempfile.mkdtemp(prefix=\"csv-harness-empty-\")\n    csv_path = os.path.join(tmp, \"empty.csv\")\n    out_path = os.path.join(tmp, \"out.json\")\n    with open(csv_path, \"w\", encoding=\"utf-8\") as f:\n        f.write(\"name,score\\n\")\n    err = _safe_call_summarize(csv_path, out_path)\n    if err:\n        _empty_run._cache = {\"_error\": err}  # type: ignore[attr-defined]\n        return _empty_run._cache  # type: ignore[attr-defined]\n    out = _read_json(out_path)\n    if out is None:\n        _empty_run._cache = {\"_error\": f\"output file not valid JSON at {out_path}\"}  # type: ignore[attr-defined]\n    else:\n        _empty_run._cache = out  # type: ignore[attr-defined]\n    return _empty_run._cache  # type: ignore[attr-defined]\n\n\ndef _check_count() -> tuple[bool, str]:\n    out = _populated_run() or {}\n    if \"_error\" in out:\n        return False, out[\"_error\"]\n    if out.get(\"count\") == 3:\n        return True, \"count=3\"\n    return False, f\"expected count=3, got {out.get('count')!r}\"\n\n\ndef _check_mean() -> tuple[bool, str]:\n    out = _populated_run() or {}\n    if \"_error\" in out:\n        return False, out[\"_error\"]\n    expected = (87 + 92 + 71) / 3.0\n    actual = out.get(\"mean_score\")\n    if isinstance(actual, (int, float)) and abs(actual - expected) <= 0.001:\n        return True, f\"mean_score={actual}\"\n    return False, f\"expected ~{expected:.3f}, got {actual!r}\"\n\n\ndef _check_max() -> tuple[bool, str]:\n    out = _populated_run() or {}\n    if \"_error\" in out:\n        return False, out[\"_error\"]\n    mx = out.get(\"max\")\n    if isinstance(mx, dict) and mx.get(\"name\") == \"Bob\" and mx.get(\"score\") == 92:\n        return True, \"max=Bob/92\"\n    return False, f\"expected max={{name:'Bob',score:92}}, got {mx!r}\"\n\n\ndef _check_min() -> tuple[bool, str]:\n    out = _populated_run() or {}\n    if \"_error\" in out:\n        return False, out[\"_error\"]\n    mn = out.get(\"min\")\n    if isinstance(mn, dict) and mn.get(\"name\") == \"Carol\" and mn.get(\"score\") == 71:\n        return True, \"min=Carol/71\"\n    return False, f\"expected min={{name:'Carol',score:71}}, got {mn!r}\"\n\n\ndef _check_empty() -> tuple[bool, str]:\n    out = _empty_run() or {}\n    if \"_error\" in out:\n        return False, out[\"_error\"]\n    if out == {\"count\": 0}:\n        return True, \"empty handled\"\n    return False, f\"expected exactly {{count:0}}, got {out!r}\"\n\n\ndef _check_code_quality() -> tuple[bool, str]:\n    \"\"\"Heuristic: source imports csv (the stdlib module) and json. We\n    pass if BOTH imports are present \u2014 a candidate using a manual CSV\n    parser is doing extra work.\"\"\"\n    try:\n        with open(\"summarize.py\", encoding=\"utf-8\") as f:\n            src = f.read()\n    except Exception as e:\n        return False, f\"couldn't read summarize.py: {e}\"\n    if \"import csv\" in src and \"import json\" in src:\n        return True, \"uses stdlib csv + json\"\n    missing = []\n    if \"import csv\" not in src:\n        missing.append(\"csv\")\n    if \"import json\" not in src:\n        missing.append(\"json\")\n    return False, f\"missing stdlib imports: {missing}\"\n\n\nCRITERIA = [\n    (\"count_correct\", 0.15, _check_count),\n    (\"mean_score_correct\", 0.2, _check_mean),\n    (\"max_correct\", 0.2, _check_max),\n    (\"min_correct\", 0.2, _check_min),\n    (\"empty_csv_returns_count_zero\", 0.15, _check_empty),\n    (\"code_quality\", 0.1, _check_code_quality),\n]\n\n\ndef main() -> None:\n    sys.path.insert(0, \".\")  # so `from summarize import summarize` resolves\n    started = time.monotonic()\n    out_criteria: list[dict[str, Any]] = []\n    score = 0.0\n    for cid, weight, fn in CRITERIA:\n        try:\n            ok, logs = fn()\n        except Exception:\n            ok, logs = False, f\"check raised: {traceback.format_exc()[:500]}\"\n        out_criteria.append({\"id\": cid, \"passed\": bool(ok), \"weight\": weight, \"logs\": logs})\n        if ok:\n            score += weight\n    duration_ms = int((time.monotonic() - started) * 1000)\n    print(json.dumps({\"criteria\": out_criteria, \"score\": round(score, 3), \"duration_ms\": duration_ms}))\n\n\nif __name__ == \"__main__\":\n    main()\n"
      }
    ],
    "rubric": {
      "items": [
        {
          "id": "count_correct",
          "label": "Count is correct",
          "weight": 0.15,
          "prompt": "Does the output's count match the number of data rows?"
        },
        {
          "id": "mean_score_correct",
          "label": "Mean is correct",
          "weight": 0.2,
          "prompt": "Does mean_score equal sum(scores)/count, with reasonable precision?"
        },
        {
          "id": "max_correct",
          "label": "Max identified",
          "weight": 0.2,
          "prompt": "Does max.name and max.score match the highest-score row?"
        },
        {
          "id": "min_correct",
          "label": "Min identified",
          "weight": 0.2,
          "prompt": "Does min.name and min.score match the lowest-score row?"
        },
        {
          "id": "empty_csv_returns_count_zero",
          "label": "Empty CSV handled",
          "weight": 0.15,
          "prompt": "On an empty (header-only) CSV, does the output equal {count: 0} (no other keys)?"
        },
        {
          "id": "code_quality",
          "label": "Code quality",
          "weight": 0.1,
          "prompt": "Does the candidate use the stdlib csv module idiomatically? Single-pass reasonable?"
        }
      ]
    },
    "topics": [
      "data-cleaning",
      "stdlib"
    ],
    "companies": [
      "Stripe",
      "Snowflake"
    ]
  },
  {
    "slug": "event-bus-ts",
    "title": "Event Bus",
    "difficulty": "easy",
    "language": "typescript",
    "time_budget_min": 60,
    "ai_policy": "off",
    "entrypoint": "node --experimental-strip-types harness/run.ts",
    "prompt_md": "# Event Bus\n\nImplement an in-memory pub/sub event bus in `eventBus.ts`.\n\n## Contract\n\n```ts\nexport type Listener<T = unknown> = (data: T) => void;\n\nexport class EventBus {\n  // Subscribe `fn` to `event`. Returns an unsubscribe function \u2014 calling\n  // it removes this listener and only this listener (the same fn may be\n  // subscribed multiple times; each subscription is independent).\n  on<T>(event: string, fn: Listener<T>): () => void;\n\n  // Emit `data` to every current listener of `event`, in registration\n  // order. Listeners registered for OTHER events are not called.\n  // If a listener throws, the remaining listeners must still be called.\n  emit<T>(event: string, data: T): void;\n}\n```\n\n## Constraints\n\n- TypeScript, no external deps. The harness runs via `node --experimental-strip-types`.\n- A given function can be subscribed multiple times. Each subscription is independent (the unsubscribe handle for one subscription doesn't affect others).\n- A listener throwing during `emit` MUST NOT prevent remaining listeners from running.\n\n## Deliverables\n\n- `eventBus.ts` exporting the `EventBus` class and `Listener` type.\n- Optional: `NOTES.md` with any trade-off you made.\n\n## Time budget\n\n~1 hour.\n",
    "starter_files": [
      {
        "path": "NOTES.md",
        "contents": "# Notes\n\nUse this file to record design decisions or trade-offs the reviewer should know about.\n"
      },
      {
        "path": "eventBus.ts",
        "contents": "/**\n * EventBus \u2014 implement on() and emit().\n *\n * See prompt.md for the contract.\n */\nexport type Listener<T = unknown> = (data: T) => void;\n\nexport class EventBus {\n  on<T>(_event: string, _fn: Listener<T>): () => void {\n    throw new Error(\"not implemented\");\n  }\n\n  emit<T>(_event: string, _data: T): void {\n    throw new Error(\"not implemented\");\n  }\n}\n"
      }
    ],
    "harness_files": [
      {
        "path": "harness/run.ts",
        "contents": "/**\n * Grading harness for event-bus-ts.\n *\n * Imports the candidate's EventBus, runs scenarios, emits one JSON\n * line on stdout matching the take-home runner contract:\n *   {\"criteria\": [{\"id\":..., \"passed\":..., \"weight\":..., \"logs\":...}, ...],\n *    \"score\": <weighted sum>, \"duration_ms\": <int>}\n *\n * Path: this file is at <workdir>/harness/run.ts; the candidate's\n * source is at <workdir>/eventBus.ts. Hence the import below.\n */\nimport { EventBus } from \"../eventBus.ts\";\n\ntype Check = () => Promise<{ passed: boolean; logs: string }> | { passed: boolean; logs: string };\n\nasync function safeRun(fn: Check): Promise<{ passed: boolean; logs: string }> {\n  try {\n    const r = fn();\n    return r instanceof Promise ? await r : r;\n  } catch (e) {\n    return { passed: false, logs: `check threw: ${(e as Error).stack ?? String(e)}`.slice(0, 500) };\n  }\n}\n\nconst checkSingleSubscriber: Check = () => {\n  const bus = new EventBus();\n  let received: unknown = null;\n  bus.on<number>(\"ping\", (n) => { received = n; });\n  bus.emit(\"ping\", 42);\n  if (received === 42) return { passed: true, logs: \"ok\" };\n  return { passed: false, logs: `expected 42, got ${String(received)}` };\n};\n\nconst checkMultipleSubscribers: Check = () => {\n  const bus = new EventBus();\n  const calls: number[] = [];\n  bus.on<number>(\"data\", (n) => calls.push(n + 1));\n  bus.on<number>(\"data\", (n) => calls.push(n * 2));\n  bus.emit(\"data\", 5);\n  if (calls.length === 2 && calls.includes(6) && calls.includes(10)) {\n    return { passed: true, logs: `calls=${JSON.stringify(calls)}` };\n  }\n  return { passed: false, logs: `expected calls to contain 6 and 10, got ${JSON.stringify(calls)}` };\n};\n\nconst checkUnsubscribe: Check = () => {\n  const bus = new EventBus();\n  let count = 0;\n  const off = bus.on(\"evt\", () => { count++; });\n  bus.emit(\"evt\", null);\n  off();\n  bus.emit(\"evt\", null);\n  if (count === 1) return { passed: true, logs: \"ok\" };\n  return { passed: false, logs: `expected count=1 after unsubscribe, got ${count}` };\n};\n\nconst checkNoCrossEventLeakage: Check = () => {\n  const bus = new EventBus();\n  let aHits = 0;\n  let bHits = 0;\n  bus.on(\"a\", () => { aHits++; });\n  bus.on(\"b\", () => { bHits++; });\n  bus.emit(\"a\", null);\n  bus.emit(\"a\", null);\n  if (aHits === 2 && bHits === 0) return { passed: true, logs: \"ok\" };\n  return { passed: false, logs: `expected aHits=2,bHits=0; got aHits=${aHits},bHits=${bHits}` };\n};\n\nconst checkThrowingSubscriberDoesNotBlock: Check = () => {\n  const bus = new EventBus();\n  let secondCalled = false;\n  bus.on(\"evt\", () => { throw new Error(\"boom\"); });\n  bus.on(\"evt\", () => { secondCalled = true; });\n  try {\n    bus.emit(\"evt\", null);\n  } catch {\n    return { passed: false, logs: \"emit() must not propagate listener exceptions\" };\n  }\n  if (secondCalled) return { passed: true, logs: \"ok\" };\n  return { passed: false, logs: \"second subscriber not called after first threw\" };\n};\n\nconst checkCodeQuality: Check = async () => {\n  // Heuristic: look at the source file. Pass if EITHER:\n  //   - imports/uses Map<...> / Map.prototype as the storage, OR\n  //   - uses a Record/object keyed by event name (less ideal but acceptable),\n  // AND the on() method returns a function (object literal storage with\n  // `[event, fn]` tuples is what we don't want).\n  const fs = await import(\"node:fs/promises\");\n  const src = await fs.readFile(\"eventBus.ts\", \"utf-8\").catch(() => \"\");\n  if (src.includes(\"Map\") && src.includes(\"get\") && src.includes(\"set\")) {\n    return { passed: true, logs: \"uses Map storage\" };\n  }\n  if (/Record<\\s*string\\s*,/.test(src) || /:\\s*\\{\\s*\\[/.test(src)) {\n    return { passed: true, logs: \"uses object/Record storage\" };\n  }\n  return { passed: false, logs: \"no Map or Record-keyed storage found in eventBus.ts\" };\n};\n\nconst CRITERIA: Array<{ id: string; weight: number; check: Check }> = [\n  { id: \"single_subscriber_receives_emit\", weight: 0.2, check: checkSingleSubscriber },\n  { id: \"multiple_subscribers_all_called\", weight: 0.2, check: checkMultipleSubscribers },\n  { id: \"unsubscribe_returned_function\", weight: 0.2, check: checkUnsubscribe },\n  { id: \"no_cross_event_leakage\", weight: 0.15, check: checkNoCrossEventLeakage },\n  { id: \"throwing_subscriber_does_not_block_others\", weight: 0.15, check: checkThrowingSubscriberDoesNotBlock },\n  { id: \"code_quality\", weight: 0.1, check: checkCodeQuality },\n];\n\nasync function main(): Promise<void> {\n  const started = performance.now();\n  const out: Array<{ id: string; passed: boolean; weight: number; logs: string }> = [];\n  let score = 0;\n  for (const { id, weight, check } of CRITERIA) {\n    const { passed, logs } = await safeRun(check);\n    out.push({ id, passed, weight, logs });\n    if (passed) score += weight;\n  }\n  const durationMs = Math.round(performance.now() - started);\n  process.stdout.write(JSON.stringify({ criteria: out, score: Math.round(score * 1000) / 1000, duration_ms: durationMs }) + \"\\n\");\n}\n\nmain().catch((e) => {\n  process.stderr.write(`harness fatal: ${(e as Error).stack ?? String(e)}\\n`);\n  process.stdout.write(JSON.stringify({\n    criteria: CRITERIA.map(({ id, weight }) => ({ id, passed: false, weight, logs: \"harness fatal\" })),\n    score: 0,\n    duration_ms: 0,\n  }) + \"\\n\");\n});\n"
      }
    ],
    "rubric": {
      "items": [
        {
          "id": "single_subscriber_receives_emit",
          "label": "Single subscriber receives emit",
          "weight": 0.2,
          "prompt": "Does on(event, fn) followed by emit(event, data) call fn with data?"
        },
        {
          "id": "multiple_subscribers_all_called",
          "label": "Multiple subscribers all called",
          "weight": 0.2,
          "prompt": "Do multiple subscribers all receive the same emit?"
        },
        {
          "id": "unsubscribe_returned_function",
          "label": "Unsubscribe via returned fn",
          "weight": 0.2,
          "prompt": "Does the function returned by on() unsubscribe that listener so subsequent emits don't call it?"
        },
        {
          "id": "no_cross_event_leakage",
          "label": "No cross-event leakage",
          "weight": 0.15,
          "prompt": "Does emit('a',...) NOT invoke listeners registered on('b',...)?"
        },
        {
          "id": "throwing_subscriber_does_not_block_others",
          "label": "Throwing subscriber doesn't block others",
          "weight": 0.15,
          "prompt": "If one subscriber throws during emit, do the remaining subscribers still receive the event?"
        },
        {
          "id": "code_quality",
          "label": "Code quality",
          "weight": 0.1,
          "prompt": "Does the implementation use a Map or similar idiomatic structure (not a flat array of [event,fn] tuples)?"
        }
      ]
    },
    "topics": [
      "pub-sub",
      "data-structures"
    ],
    "companies": [
      "Cloudflare",
      "Discord"
    ]
  },
  {
    "slug": "kv-store-py",
    "title": "Tiny KV Store",
    "difficulty": "easy",
    "language": "python",
    "time_budget_min": 60,
    "ai_policy": "off",
    "entrypoint": "python3 harness/run.py",
    "prompt_md": "# Tiny KV Store\n\nImplement a small in-memory key-value store as a pure dispatch function.\n\n## Contract\n\nYour job is to fill in `handle(method: str, path: str, body: dict | None = None) -> tuple[int, dict]` in `app.py`.\n\nThe function must support these routes:\n\n| Method | Path           | Body                       | Response                                         |\n|--------|----------------|----------------------------|--------------------------------------------------|\n| POST   | `/set/<key>`   | `{\"value\": <any>}`         | `(200, {\"ok\": True})` \u2014 stores the value         |\n| GET    | `/get/<key>`   | (none)                     | `(200, {\"value\": <stored>})` or `(404, {\"error\": \"not found\"})` |\n| DELETE | `/del/<key>`   | (none)                     | `(200, {\"ok\": True})` \u2014 idempotent on missing    |\n| GET    | `/list`        | (none)                     | `(200, {\"keys\": [<sorted list>]})`               |\n\nState persists across calls within the same process.\n\n## Deliverables\n\n- A working `app.py` with `handle(method, path, body)` implemented.\n- Optional: a short note in `NOTES.md` explaining your dispatch approach (e.g., regex routes, or a tiny route table) and any trade-offs.\n\n## What we're looking for\n\n- Correctness on all four routes.\n- Clean dispatch (avoid a giant if/elif chain on path strings).\n- Clear error responses.\n- The candidate uses Python's standard library only \u2014 no external deps.\n\n## Time budget\n\nRoughly 1 hour. The grading harness runs in a few seconds.\n",
    "starter_files": [
      {
        "path": "NOTES.md",
        "contents": "# Notes\n\nUse this file to record design decisions or trade-offs the reviewer should know about.\n"
      },
      {
        "path": "app.py",
        "contents": "\"\"\"Tiny KV Store \u2014 implement handle().\"\"\"\nfrom __future__ import annotations\n\n\ndef handle(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:\n    \"\"\"Dispatch (method, path) to the appropriate operation.\n\n    See prompt.md for the route contract.\n    \"\"\"\n    return 501, {\"error\": \"not implemented\"}\n"
      }
    ],
    "harness_files": [
      {
        "path": "harness/run.py",
        "contents": "\"\"\"Grading harness for kv-store-py.\n\nImports the candidate's `app.handle` and exercises every route. Emits\na single line of JSON on stdout matching the take-home runner's\ncontract:  {\"criteria\": [...], \"score\": float, \"duration_ms\": int}.\n\nThe harness must NOT import anything that fails on a stub starter \u2014 a\ncandidate who hasn't implemented anything yet should still see a\nclean 0.0 score with informative `logs` per criterion.\"\"\"\nfrom __future__ import annotations\n\nimport json\nimport sys\nimport time\nimport traceback\nfrom typing import Any\n\n\ndef _safe_call(method: str, path: str, body: dict | None = None) -> tuple[Any, str]:\n    \"\"\"Returns (result_or_None, error_text). Catches all exceptions.\"\"\"\n    try:\n        from app import handle\n    except Exception:\n        return None, f\"couldn't import app.handle: {traceback.format_exc()[:500]}\"\n    try:\n        return handle(method, path, body), \"\"\n    except Exception:\n        return None, f\"handle() raised: {traceback.format_exc()[:500]}\"\n\n\ndef _check_set_returns_ok() -> tuple[bool, str]:\n    res, err = _safe_call(\"POST\", \"/set/alpha\", {\"value\": 1})\n    if err:\n        return False, err\n    if not (isinstance(res, tuple) and len(res) == 2):\n        return False, f\"expected (status, body) tuple, got {res!r}\"\n    status, body = res\n    if status != 200:\n        return False, f\"expected status 200, got {status}\"\n    if body != {\"ok\": True}:\n        return False, f\"expected body {{ok: True}}, got {body!r}\"\n    return True, \"ok\"\n\n\ndef _check_get_returns_stored_value() -> tuple[bool, str]:\n    _safe_call(\"POST\", \"/set/beta\", {\"value\": \"hello\"})\n    res, err = _safe_call(\"GET\", \"/get/beta\")\n    if err:\n        return False, err\n    if not (isinstance(res, tuple) and len(res) == 2):\n        return False, f\"expected (status, body) tuple, got {res!r}\"\n    status, body = res\n    if status != 200 or body != {\"value\": \"hello\"}:\n        return False, f\"expected (200, {{value: 'hello'}}), got ({status}, {body!r})\"\n    return True, \"ok\"\n\n\ndef _check_get_missing_404() -> tuple[bool, str]:\n    res, err = _safe_call(\"GET\", \"/get/never-set\")\n    if err:\n        return False, err\n    if not (isinstance(res, tuple) and len(res) == 2):\n        return False, f\"expected (status, body) tuple, got {res!r}\"\n    status, body = res\n    if status != 404:\n        return False, f\"expected status 404, got {status}\"\n    if not isinstance(body, dict) or \"error\" not in body:\n        return False, f\"expected body with 'error' key, got {body!r}\"\n    return True, \"ok\"\n\n\ndef _check_delete_removes() -> tuple[bool, str]:\n    _safe_call(\"POST\", \"/set/gamma\", {\"value\": 42})\n    res, err = _safe_call(\"DELETE\", \"/del/gamma\")\n    if err:\n        return False, err\n    if not (isinstance(res, tuple) and len(res) == 2 and res[0] == 200):\n        return False, f\"DELETE expected (200, {{ok: True}}), got {res!r}\"\n    # Verify it's gone.\n    res2, err2 = _safe_call(\"GET\", \"/get/gamma\")\n    if err2 or not (isinstance(res2, tuple) and res2[0] == 404):\n        return False, f\"after DELETE, GET should 404; got {res2!r}\"\n    # Idempotent \u2014 DELETE again shouldn't raise.\n    res3, err3 = _safe_call(\"DELETE\", \"/del/gamma\")\n    if err3:\n        return False, f\"DELETE on missing key raised: {err3}\"\n    if not (isinstance(res3, tuple) and res3[0] == 200):\n        return False, f\"DELETE on missing key should still 200; got {res3!r}\"\n    return True, \"ok\"\n\n\ndef _check_list_returns_sorted_keys() -> tuple[bool, str]:\n    _safe_call(\"POST\", \"/set/banana\", {\"value\": 1})\n    _safe_call(\"POST\", \"/set/apple\", {\"value\": 2})\n    _safe_call(\"POST\", \"/set/cherry\", {\"value\": 3})\n    res, err = _safe_call(\"GET\", \"/list\")\n    if err:\n        return False, err\n    if not (isinstance(res, tuple) and len(res) == 2):\n        return False, f\"expected (status, body) tuple, got {res!r}\"\n    status, body = res\n    if status != 200 or not isinstance(body, dict) or \"keys\" not in body:\n        return False, f\"expected (200, {{keys: [...]}}), got ({status}, {body!r})\"\n    keys = body[\"keys\"]\n    # apple, banana, cherry should appear (plus alpha, beta, possibly gamma was deleted).\n    expected = {\"alpha\", \"beta\", \"apple\", \"banana\", \"cherry\"}\n    found = set(keys)\n    if not expected.issubset(found):\n        return False, f\"missing expected keys: {expected - found}\"\n    if list(keys) != sorted(keys):\n        return False, f\"expected sorted, got {keys!r}\"\n    return True, \"ok\"\n\n\ndef _check_code_quality() -> tuple[bool, str]:\n    \"\"\"Crude objective check: source uses some form of dispatch other\n    than a flat if/elif chain across all routes. We pass if EITHER:\n      - a `dict` is used as a route table, OR\n      - a `re` import + match is used, OR\n      - the source has fewer than 8 'if ' / 'elif ' tokens combined,\n        suggesting compact dispatch.\n    Subjective judgment is left to the AI rubric layer.\"\"\"\n    try:\n        with open(\"app.py\", encoding=\"utf-8\") as f:\n            src = f.read()\n    except Exception as e:\n        return False, f\"couldn't read app.py: {e}\"\n    if \"import re\" in src and \"match\" in src:\n        return True, \"uses regex routing\"\n    if \"{\" in src and \"}\" in src and (\"lambda\" in src or \"def \" in src):\n        # Very loose heuristic \u2014 a dict + functions probably means a route table.\n        if_count = src.count(\"if \") + src.count(\"elif \")\n        if if_count < 6:\n            return True, \"compact dispatch (few branches)\"\n        return False, f\"dispatch looks long ({if_count} if/elif tokens)\"\n    if_count = src.count(\"if \") + src.count(\"elif \")\n    if if_count < 8:\n        return True, \"compact dispatch\"\n    return False, f\"flat if/elif chain detected ({if_count} branches)\"\n\n\nCRITERIA = [\n    (\"set_returns_ok\", 0.2, _check_set_returns_ok),\n    (\"get_returns_stored_value\", 0.2, _check_get_returns_stored_value),\n    (\"get_missing_404\", 0.15, _check_get_missing_404),\n    (\"delete_removes\", 0.2, _check_delete_removes),\n    (\"list_returns_sorted_keys\", 0.15, _check_list_returns_sorted_keys),\n    (\"code_quality\", 0.1, _check_code_quality),\n]\n\n\ndef main() -> None:\n    sys.path.insert(0, \".\")  # so `from app import handle` resolves\n    started = time.monotonic()\n    out_criteria: list[dict[str, Any]] = []\n    score = 0.0\n    for cid, weight, fn in CRITERIA:\n        try:\n            ok, logs = fn()\n        except Exception:\n            ok, logs = False, f\"check raised: {traceback.format_exc()[:500]}\"\n        out_criteria.append({\"id\": cid, \"passed\": bool(ok), \"weight\": weight, \"logs\": logs})\n        if ok:\n            score += weight\n    duration_ms = int((time.monotonic() - started) * 1000)\n    print(json.dumps({\"criteria\": out_criteria, \"score\": round(score, 3), \"duration_ms\": duration_ms}))\n\n\nif __name__ == \"__main__\":\n    main()\n"
      }
    ],
    "rubric": {
      "items": [
        {
          "id": "set_returns_ok",
          "label": "POST /set works",
          "weight": 0.2,
          "prompt": "Does POST /set/{key} accept and store the value, returning (200, {ok: True})?"
        },
        {
          "id": "get_returns_stored_value",
          "label": "GET /get returns set value",
          "weight": 0.2,
          "prompt": "After a successful set, does GET /get/{key} return (200, {value: ...}) with the stored value?"
        },
        {
          "id": "get_missing_404",
          "label": "GET /get of missing key 404s",
          "weight": 0.15,
          "prompt": "Does GET /get of an unset key return 404 with an error body?"
        },
        {
          "id": "delete_removes",
          "label": "DELETE removes key",
          "weight": 0.2,
          "prompt": "Does DELETE /del/{key} remove the key (so subsequent GET 404s)? Idempotent \u2014 succeeds on missing keys too?"
        },
        {
          "id": "list_returns_sorted_keys",
          "label": "GET /list returns sorted keys",
          "weight": 0.15,
          "prompt": "Does GET /list return all current keys, sorted?"
        },
        {
          "id": "code_quality",
          "label": "Code quality",
          "weight": 0.1,
          "prompt": "Is dispatch idiomatic (no spaghetti if/elif chain)? Helpful error handling?"
        }
      ]
    },
    "topics": [
      "backend",
      "data-structures"
    ],
    "companies": [
      "Stripe",
      "Plaid"
    ]
  }
];

migrate(
  (db) => {
    const dao = new Dao(db);
    const coll = dao.findCollectionByNameOrId("take_home_assignments");
    for (const a of ASSIGNMENTS) {
      try {
        const old = dao.findFirstRecordByData("take_home_assignments", "slug", a.slug);
        dao.deleteRecord(old);
      } catch (_) { /* not present */ }
      const rec = new Record(coll, {
        slug: a.slug,
        title: a.title,
        difficulty: a.difficulty,
        language: a.language,
        entrypoint: a.entrypoint,
        time_budget_min: a.time_budget_min,
        ai_policy: a.ai_policy,
        prompt_md: a.prompt_md,
        starter_files: a.starter_files,
        harness_files: a.harness_files,
        rubric: a.rubric,
        topics: a.topics,
        companies: a.companies,
      });
      dao.saveRecord(rec);
    }
  },
  (db) => {
    const dao = new Dao(db);
    for (const a of ASSIGNMENTS) {
      try {
        const rec = dao.findFirstRecordByData("take_home_assignments", "slug", a.slug);
        dao.deleteRecord(rec);
      } catch (_) { /* ignore */ }
    }
  },
);
