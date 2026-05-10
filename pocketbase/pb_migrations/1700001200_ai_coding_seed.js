/// <reference path="../pb_data/types.d.ts" />

const ROUNDS = [
  {
    "slug": "async-bugs-py",
    "title": "Async Worker \u2014 Critical Verification",
    "difficulty": "hard",
    "language": "python",
    "description": "An AI-generated async worker module is supposedly complete. Its visible tests pass \u2014 but does the implementation actually do what the prompt asked? Read carefully; the bug is subtle.",
    "checkpoints": [
      {
        "label": "Verify the worker",
        "prompt": "The starter worker.py was written by an AI assistant. The visible tests pass. Read the prompt at the top of worker.py against the implementation. Find and fix the bug. (Hidden tests will run on submission.)",
        "ai_allowed": true,
        "test_command": "pytest -q tests/checkpoint_0/",
        "tests_glob": "tests/**/*.py",
        "hidden_files": [
          {
            "path": "tests/checkpoint_0/test_hidden.py",
            "contents": "import asyncio\nimport time\nfrom worker import run_all\n\n\ndef test_returns_list_of_all_results():\n    async def coro(n):\n        await asyncio.sleep(0)\n        return n * 10\n\n    out = asyncio.run(run_all([coro(1), coro(2), coro(3)]))\n    assert out == [10, 20, 30], f\"expected list of all results, got {out!r}\"\n\n\ndef test_runs_concurrently():\n    async def coro(d):\n        await asyncio.sleep(d)\n        return d\n\n    start = time.monotonic()\n    out = asyncio.run(run_all([coro(0.1), coro(0.1), coro(0.1)]))\n    elapsed = time.monotonic() - start\n    assert out == [0.1, 0.1, 0.1]\n    assert elapsed < 0.25, f\"expected concurrent (~0.1s), took {elapsed:.3f}s\"\n"
          }
        ]
      }
    ],
    "rubric": {
      "items": [
        {
          "id": "bug_caught",
          "label": "Bug caught",
          "weight": 0.6,
          "prompt": "Did the candidate identify and fix the divergence between worker.py's docstring and its behavior?"
        },
        {
          "id": "code_quality",
          "label": "Code quality",
          "weight": 0.2,
          "prompt": "Is the fix minimal and idiomatic?"
        },
        {
          "id": "verification_habits",
          "label": "Verification habits",
          "weight": 0.2,
          "prompt": "Did the candidate's chats show probing/skepticism toward the AI-generated starter, or did they trust it at face value?"
        }
      ]
    },
    "topics": [
      "asyncio",
      "code-review"
    ],
    "companies": [
      "Meta"
    ],
    "starter_files": [
      {
        "path": "worker.py",
        "contents": "\"\"\"Async worker.\n\nSpec:\n  - run_all(coros) takes a list of coroutines and returns a list of\n    their results in order.\n  - All coroutines run concurrently \u2014 total wall time should be ~max\n    of the individual durations, not the sum.\n\nImplementation below was AI-generated. Visible tests verify the basic\nshape; submission grades probe deeper invariants.\n\"\"\"\nimport asyncio\n\n\nasync def run_all(coros):\n    results = await asyncio.gather(*coros)\n    return results[0]\n"
      },
      {
        "path": "tests/checkpoint_0/test_visible.py",
        "contents": "import asyncio\nfrom worker import run_all\n\n\n# Visible tests intentionally exercise the API without strict\n# assertions on the return shape. They confirm run_all completes\n# without raising, which is true for both the buggy and correct\n# implementations. The hidden suite is what verifies semantics \u2014\n# this is a critical-verification round, after all.\n\n\ndef test_runs_without_raising():\n    async def coro():\n        return 42\n\n    # Under both the bug (returns 42) and a correct fix (returns [42]),\n    # the call completes without raising and returns a truthy value.\n    result = asyncio.run(run_all([coro()]))\n    assert result  # truthy under both 42 and [42]\n"
      }
    ]
  },
  {
    "slug": "cart-bugfix-py",
    "title": "Shopping Cart \u2014 bug, feature, optimize",
    "difficulty": "medium",
    "language": "python",
    "description": "A tiny shopping cart library is failing tests. Diagnose and fix, then add discount-code support, then optimize the price loop.",
    "topics": [
      "debugging",
      "testing",
      "refactor"
    ],
    "companies": [
      "meta"
    ],
    "checkpoints": [
      {
        "label": "Bug fix",
        "prompt": "Three tests in `tests/test_checkpoint.py` fail. Find the bug in `cart.py` and fix it. Don't change the tests.",
        "ai_allowed": false,
        "test_command": "pytest tests/checkpoint_0/test_checkpoint.py -q",
        "tests_glob": "tests/**/*.py",
        "hidden_files": [
          {
            "path": "tests/checkpoint_0/test_hidden.py",
            "contents": "import json, pathlib\n\n# A trivial hidden assertion to verify the hidden-test pipeline. The\n# real critical-verification round (async-bugs-py, Task 1.4) is where\n# this matters.\ndef test_discounts_file_present():\n    root = pathlib.Path(__file__).resolve().parents[2]  # workdir root\n    data = json.loads((root / \"discounts.json\").read_text())\n    assert \"BLACKFRIDAY50\" in data\n"
          }
        ]
      },
      {
        "label": "Feature: discount codes",
        "prompt": "Implement `apply_discount_code(cart, code)` in `cart.py`. Codes are loaded from `discounts.json`. Make the tests in `tests/test_checkpoint.py` pass.",
        "ai_allowed": true,
        "test_command": "pytest tests/checkpoint_1/test_checkpoint.py -q",
        "tests_glob": "tests/**/*.py",
        "hidden_files": []
      },
      {
        "label": "Optimize",
        "prompt": "`total(cart)` is O(n*m) over items \u00d7 discounts. Make it O(n+m) without changing the API. Tests cover correctness; the timing harness `tests/test_checkpoint.py::test_perf` enforces the bound.",
        "ai_allowed": true,
        "test_command": "pytest tests/checkpoint_2/test_checkpoint.py -q",
        "tests_glob": "tests/**/*.py",
        "hidden_files": []
      }
    ],
    "rubric": {
      "items": [
        {
          "id": "correctness",
          "label": "Correctness",
          "weight": 0.4,
          "prompt": "Did all checkpoint tests pass at submit time?"
        },
        {
          "id": "code_quality",
          "label": "Code quality",
          "weight": 0.2,
          "prompt": "Is the final code idiomatic Python? Naming, structure, type hints, no dead code."
        },
        {
          "id": "design",
          "label": "Design",
          "weight": 0.2,
          "prompt": "Are the bug fix, feature, and optimization integrated cleanly? No layering violations or duplicated logic."
        },
        {
          "id": "verification",
          "label": "Verification habits",
          "weight": 0.2,
          "prompt": "Examining the chat history, did the candidate verify AI suggestions or accept them blindly? This is a coaching signal, not a punishment \u2014 explain what you see."
        }
      ]
    },
    "starter_files": [
      {
        "path": "README.md",
        "contents": "A tiny shopping cart. Run `pytest tests/test_checkpoint.py -q` to see failing tests.\n"
      },
      {
        "path": "cart.py",
        "contents": "from typing import List, Dict\n\ndef total(cart: List[Dict], discounts: Dict[str, float] | None = None) -> float:\n    discounts = discounts or {}\n    subtotal = 0.0\n    for item in cart:\n        # The math here doesn't agree with what the tests assert.\n        # Find what's wrong and fix it.\n        subtotal += item[\"qty\"] // 1 * item[\"unit_price\"]\n    return round(subtotal, 2)\n\ndef apply_discount_code(cart, code):\n    # Implemented in the discount-codes checkpoint.\n    raise NotImplementedError\n"
      },
      {
        "path": "discounts.json",
        "contents": "{ \"WELCOME10\": 0.10, \"VIP20\": 0.20, \"BLACKFRIDAY50\": 0.50 }\n"
      },
      {
        "path": "tests/checkpoint_0/test_checkpoint.py",
        "contents": "from cart import total\n\ndef test_simple_total():\n    assert total([{\"qty\": 2.5, \"unit_price\": 10}]) == 25.0\n\ndef test_fractional_quantity():\n    assert total([{\"qty\": 1.5, \"unit_price\": 10}]) == 15.0\n\ndef test_multi_item():\n    # Two fractional quantities; both lines must use float math for the\n    # total to come out right. Buggy floor-divide gives 10.0+15.0 = 25.0.\n    assert total([{\"qty\": 1.5, \"unit_price\": 10.0}, {\"qty\": 3.5, \"unit_price\": 4.0}]) == 29.0\n"
      },
      {
        "path": "tests/checkpoint_1/test_checkpoint.py",
        "contents": "from cart import total, apply_discount_code\n\ndef test_welcome_code_takes_10pct():\n    cart = [{\"qty\": 2, \"unit_price\": 10}]\n    apply_discount_code(cart, \"WELCOME10\")\n    assert total(cart) == 18.00\n\ndef test_unknown_code_is_noop_and_returns_false():\n    cart = [{\"qty\": 2, \"unit_price\": 10}]\n    assert apply_discount_code(cart, \"BOGUS\") is False\n    assert total(cart) == 20.00\n\ndef test_blackfriday_code_takes_50pct():\n    # This code only exists in discounts.json. A solution that hardcodes\n    # WELCOME10 / VIP20 will fail this test.\n    cart = [{\"qty\": 2, \"unit_price\": 10}]\n    apply_discount_code(cart, \"BLACKFRIDAY50\")\n    assert total(cart) == 10.00\n"
      },
      {
        "path": "tests/checkpoint_2/test_checkpoint.py",
        "contents": "import time\nfrom cart import total\n\ndef test_correctness_holds():\n    cart = [{\"qty\": 1, \"unit_price\": p} for p in range(1, 1001)]\n    assert total(cart) == 500500.00\n\ndef test_perf():\n    cart = [{\"qty\": 1, \"unit_price\": 1.0} for _ in range(20000)]\n    discounts = {f\"D{i}\": 0.01 for i in range(200)}\n    start = time.monotonic()\n    total(cart, discounts)\n    assert time.monotonic() - start < 0.5, \"total() should run linearly\"\n"
      }
    ]
  },
  {
    "slug": "log-parser-ts",
    "title": "Log Parser \u2014 bug, feature, optimize",
    "difficulty": "medium",
    "language": "typescript",
    "description": "A line-oriented log parser is failing on real-world inputs. Diagnose and fix, then add a JSON output mode, then convert string-split to a streaming iterator over lines.",
    "topics": [
      "debugging",
      "parsing",
      "streams"
    ],
    "companies": [
      "meta"
    ],
    "checkpoints": [
      {
        "label": "Bug fix",
        "prompt": "Three tests in `tests/parser.test.ts` fail. Find the bug in `parser.ts` and fix it. Don't change the tests.",
        "ai_allowed": false,
        "test_command": "node --test tests/checkpoint_0/parser.test.ts",
        "tests_glob": "tests/**/*.ts",
        "hidden_files": []
      },
      {
        "label": "Feature: JSON output",
        "prompt": "Add `toJsonLines(input: string): string` in `parser.ts`. It returns one JSON object per line, separated by `\\n`, where each object is `{ts, level, msg}` for a successfully parsed line. Skip lines that don't parse. Make the new tests in `tests/parser.test.ts` pass.",
        "ai_allowed": true,
        "test_command": "node --test tests/checkpoint_1/parser.test.ts",
        "tests_glob": "tests/**/*.ts",
        "hidden_files": []
      },
      {
        "label": "Optimize",
        "prompt": "Convert `parseAll` from a string-split-then-iterate implementation to a streaming line iterator (a generator yielding parsed `LogLine`s). The new function `parseStream(input: Iterable<string>): Iterable<LogLine>` should consume an iterable of raw lines without materializing the whole input. Existing `parseAll` should still work for callers using a single string.",
        "ai_allowed": true,
        "test_command": "node --test tests/checkpoint_2/parser.test.ts",
        "tests_glob": "tests/**/*.ts",
        "hidden_files": []
      }
    ],
    "rubric": {
      "items": [
        {
          "id": "correctness",
          "label": "Correctness",
          "weight": 0.4,
          "prompt": "Did all checkpoint tests pass at submit time?"
        },
        {
          "id": "code_quality",
          "label": "Code quality",
          "weight": 0.2,
          "prompt": "Is the final code idiomatic TypeScript? Naming, types, no dead code."
        },
        {
          "id": "design",
          "label": "Design",
          "weight": 0.2,
          "prompt": "Are the bug fix, feature, and streaming refactor integrated cleanly?"
        },
        {
          "id": "verification",
          "label": "Verification habits",
          "weight": 0.2,
          "prompt": "Examining the chat history, did the candidate verify AI suggestions or accept them blindly? This is a coaching signal."
        }
      ]
    },
    "starter_files": [
      {
        "path": "README.md",
        "contents": "A line-oriented log parser. Run `node --test tests/parser.test.ts` to see failing tests.\n"
      },
      {
        "path": "package.json",
        "contents": "{\n  \"name\": \"log-parser-ts\",\n  \"type\": \"module\",\n  \"scripts\": {\n    \"test\": \"node --test tests/parser.test.ts\"\n  }\n}\n"
      },
      {
        "path": "parser.ts",
        "contents": "export type LogLine = { ts: number; level: string; msg: string };\n\nexport function parseLine(line: string): LogLine | null {\n  // Format: \"2024-05-08T12:34:56Z [INFO] message text\"\n  const m = line.match(/^(\\S+) \\[(\\w+)] (.*)$/);\n  if (!m) return null;\n  // The timestamp parsing here doesn't agree with what the tests assert.\n  // Find what's wrong and fix it. (Don't change the message/level parsing.)\n  return { ts: Date.parse(m[1].slice(0, -3)), level: m[2], msg: m[3] };\n}\n\nexport function parseAll(input: string): LogLine[] {\n  return input.split('\\n').map(parseLine).filter((l): l is LogLine => l !== null);\n}\n"
      },
      {
        "path": "tests/checkpoint_0/parser.test.ts",
        "contents": "import { test } from 'node:test';\nimport assert from 'node:assert';\nimport { parseLine, parseAll } from '../../parser.ts';\n\nconst UTC_TS = Date.UTC(2024, 4, 8, 12, 34, 56); // 2024-05-08T12:34:56Z\n\ntest('parses a UTC timestamp', () => {\n  const r = parseLine('2024-05-08T12:34:56Z [INFO] hello');\n  assert.equal(r?.ts, UTC_TS);\n  assert.equal(r?.level, 'INFO');\n  assert.equal(r?.msg, 'hello');\n});\n\ntest('parses multiple lines and produces UTC timestamps', () => {\n  const out = parseAll('2024-05-08T12:34:56Z [INFO] a\\n2024-05-08T12:34:57Z [WARN] b');\n  assert.equal(out.length, 2);\n  assert.equal(out[0].ts, UTC_TS);\n  assert.equal(out[1].ts, Date.UTC(2024, 4, 8, 12, 34, 57));\n  assert.equal(out[0].level, 'INFO');\n  assert.equal(out[1].level, 'WARN');\n});\n\ntest('returns null for non-matching line, but still parses valid line in batch', () => {\n  assert.equal(parseLine('garbage'), null);\n  // Mix valid and invalid: invalid is filtered, valid keeps its UTC timestamp.\n  const out = parseAll('garbage\\n2024-05-08T12:34:56Z [INFO] real');\n  assert.equal(out.length, 1);\n  assert.equal(out[0].ts, UTC_TS);\n});\n"
      },
      {
        "path": "tests/checkpoint_1/parser.test.ts",
        "contents": "import { test } from 'node:test';\nimport assert from 'node:assert';\nimport { toJsonLines } from '../../parser.ts';\n\ntest('emits one JSON object per parsed line', () => {\n  const out = toJsonLines('2024-05-08T12:34:56Z [INFO] hello\\n2024-05-08T12:34:57Z [WARN] uh');\n  const lines = out.split('\\n').filter((l) => l.length > 0);\n  assert.equal(lines.length, 2);\n  const first = JSON.parse(lines[0]);\n  assert.equal(first.level, 'INFO');\n  assert.equal(first.msg, 'hello');\n  assert.equal(first.ts, Date.parse('2024-05-08T12:34:56Z'));\n});\n\ntest('skips lines that do not parse', () => {\n  const out = toJsonLines('garbage\\n2024-05-08T12:34:56Z [INFO] real');\n  const lines = out.split('\\n').filter((l) => l.length > 0);\n  assert.equal(lines.length, 1);\n});\n"
      },
      {
        "path": "tests/checkpoint_2/parser.test.ts",
        "contents": "import { test } from 'node:test';\nimport assert from 'node:assert';\nimport { parseStream, parseAll, type LogLine } from '../../parser.ts';\n\nfunction* lineSource(input: string): Iterable<string> {\n  for (const line of input.split('\\n')) yield line;\n}\n\ntest('parseStream yields parsed lines lazily', () => {\n  const src = lineSource('2024-05-08T12:34:56Z [INFO] a\\n2024-05-08T12:34:57Z [WARN] b');\n  const out: LogLine[] = [];\n  for (const line of parseStream(src)) out.push(line);\n  assert.equal(out.length, 2);\n  assert.equal(out[0].level, 'INFO');\n});\n\ntest('parseAll still works as a thin wrapper', () => {\n  const out = parseAll('2024-05-08T12:34:56Z [INFO] only');\n  assert.equal(out.length, 1);\n});\n\ntest('parseStream skips invalid lines', () => {\n  const src = lineSource('garbage\\n2024-05-08T12:34:56Z [INFO] real');\n  const out = [...parseStream(src)];\n  assert.equal(out.length, 1);\n});\n\ntest('parseStream is lazy \u2014 does not exhaust the iterable upfront', () => {\n  let pulled = 0;\n  function* counted(): Iterable<string> {\n    while (true) {\n      pulled++;\n      yield '2024-05-08T12:34:56Z [INFO] x';\n    }\n  }\n  const it = parseStream(counted())[Symbol.iterator]();\n  it.next();\n  it.next();\n  it.next();\n  // We pulled 3 lines; an eager implementation would have pulled all of\n  // them (infinite loop) or many more. Allow up to 4 to tolerate any\n  // single-line lookahead a sensible implementation might do.\n  assert.ok(pulled <= 4, `parseStream pulled ${pulled} lines for 3 next() calls`);\n});\n"
      }
    ]
  },
  {
    "slug": "rate-limiter-ts",
    "title": "Rate Limiter \u2014 Make it Fast",
    "difficulty": "medium",
    "language": "typescript",
    "description": "A sliding-window rate limiter is shipped and works correctly on small inputs. But the visible perf test (50,000 allow() calls) is failing \u2014 the naive implementation rescans the entire history on every call. Replace the inner data structure so the perf test passes without changing correctness.",
    "checkpoints": [
      {
        "label": "Optimize the limiter",
        "prompt": "rateLimiter.ts is correct but quadratic \u2014 every allow() call filters the full history. Make the perf test pass. Hint: a structure that lets you drop expired entries from one end without scanning the whole array works well.",
        "ai_allowed": true,
        "test_command": "node --test --experimental-strip-types tests/checkpoint_0/*.test.ts",
        "tests_glob": "tests/**/*.ts",
        "hidden_files": [
          {
            "path": "tests/checkpoint_0/test_hidden.test.ts",
            "contents": "import { test } from 'node:test';\nimport { strict as assert } from 'node:assert';\nimport { RateLimiter } from '../../rateLimiter.ts';\n\ntest('boundary: hit exactly at now-window edge expires', () => {\n  const rl = new RateLimiter(1, 1000);\n  assert.equal(rl.allow(0), true);\n  // now=1000 means now-window=0; the original hit at t=0 is at the\n  // boundary. Per the spec (\"previous windowMs\"), it should have aged\n  // out by t=1000 (strictly greater-than).\n  assert.equal(rl.allow(1000), true);\n});\n\ntest('many distinct hits within window', () => {\n  const rl = new RateLimiter(100, 1000);\n  for (let i = 0; i < 100; i++) {\n    assert.equal(rl.allow(i), true);\n  }\n  assert.equal(rl.allow(150), false);   // 101st within 150ms \u2014 denied\n});\n\ntest('zero limit denies everything', () => {\n  const rl = new RateLimiter(0, 1000);\n  assert.equal(rl.allow(0), false);\n  assert.equal(rl.allow(500), false);\n  assert.equal(rl.allow(2000), false);\n});\n"
          }
        ]
      }
    ],
    "rubric": {
      "items": [
        {
          "id": "performance",
          "label": "Performance fix",
          "weight": 0.5,
          "prompt": "Did the candidate move from O(n) per-call (filter) to O(1) amortized? Is the perf test passing?"
        },
        {
          "id": "correctness",
          "label": "Correctness preserved",
          "weight": 0.3,
          "prompt": "Do all correctness tests still pass? No off-by-one in the sliding window."
        },
        {
          "id": "code_quality",
          "label": "Code quality",
          "weight": 0.2,
          "prompt": "Is the optimized data structure idiomatic TypeScript? No premature abstraction."
        }
      ]
    },
    "topics": [
      "data-structures",
      "performance"
    ],
    "companies": [
      "Stripe",
      "Cloudflare"
    ],
    "starter_files": [
      {
        "path": "rateLimiter.ts",
        "contents": "/**\n * Sliding-window rate limiter.\n *\n * Spec:\n *   - allow(now: number) records a hit at time `now` (ms-since-epoch)\n *     and returns true if at most `maxRequests` requests have occurred\n *     in the previous `windowMs` (inclusive of `now`).\n *   - When the limit is hit, allow() returns false and does NOT record\n *     the rejected hit.\n *\n * Correctness tests pass against the starter. The perf test does not \u2014\n * the implementation rescans the full history on every call.\n */\nexport class RateLimiter {\n  private readonly max: number;\n  private readonly window: number;\n  private hits: number[] = [];\n\n  constructor(maxRequests: number, windowMs: number) {\n    this.max = maxRequests;\n    this.window = windowMs;\n  }\n\n  allow(now: number): boolean {\n    this.hits = this.hits.filter((t) => t > now - this.window);\n    if (this.hits.length >= this.max) return false;\n    this.hits.push(now);\n    return true;\n  }\n}\n"
      },
      {
        "path": "tests/checkpoint_0/test_perf.test.ts",
        "contents": "import { test } from 'node:test';\nimport { strict as assert } from 'node:assert';\nimport { RateLimiter } from '../../rateLimiter.ts';\n\n// Correctness \u2014 passes against the naive starter.\ntest('basic allow / deny', () => {\n  const rl = new RateLimiter(2, 1000);\n  assert.equal(rl.allow(0), true);\n  assert.equal(rl.allow(100), true);\n  assert.equal(rl.allow(200), false);   // limit hit\n  assert.equal(rl.allow(1100), true);   // earliest expired\n});\n\ntest('rejected requests are not recorded', () => {\n  const rl = new RateLimiter(1, 1000);\n  assert.equal(rl.allow(0), true);\n  assert.equal(rl.allow(100), false);   // rejected\n  assert.equal(rl.allow(100), false);   // still rejected\n  assert.equal(rl.allow(1001), true);   // first hit aged out\n});\n\n// Performance \u2014 fails against the naive O(n\u00b2) implementation. With a\n// generous limit and wide window every hit accumulates in history;\n// the naive .filter() rebuilds the full array on every call. The\n// optimized solution does this in well under 500ms on commodity\n// hardware (we measured ~3ms locally; the naive takes 10+ seconds).\ntest('handles 50k allow() calls under 500ms', () => {\n  const rl = new RateLimiter(1_000_000, 10_000_000);\n  const N = 50_000;\n  const start = performance.now();\n  for (let i = 0; i < N; i++) {\n    rl.allow(i);\n  }\n  const elapsed = performance.now() - start;\n  assert.ok(elapsed < 500, `expected < 500ms, took ${elapsed.toFixed(1)}ms`);\n});\n"
      }
    ]
  },
  {
    "slug": "word-count-py",
    "title": "Word Count \u2014 Add Punctuation Stripping",
    "difficulty": "medium",
    "language": "python",
    "description": "A baseline word-counter is shipped, but it doesn't handle punctuation \u2014 \"Hello,\" and \"hello\" count as different words. Extend it so leading/trailing punctuation is stripped before counting. Internal punctuation (apostrophes in contractions) must stay.",
    "checkpoints": [
      {
        "label": "Add punctuation stripping",
        "prompt": "The starter passes the basic-frequency tests but fails the punctuation tests. Extend wordcount.count so leading/trailing punctuation is stripped after lowercasing, while internal characters (e.g. apostrophes in contractions) are preserved. Empty tokens after stripping should NOT appear in the result.",
        "ai_allowed": true,
        "test_command": "pytest -q tests/checkpoint_0/",
        "tests_glob": "tests/**/*.py",
        "hidden_files": [
          {
            "path": "tests/checkpoint_0/test_hidden.py",
            "contents": "from wordcount import count\n\n\ndef test_empty_string_returns_empty():\n    assert count(\"\") == {}\n\n\ndef test_token_that_is_only_punctuation_is_dropped():\n    # \"...\" strips to \"\" \u2014 must NOT appear as an empty-string key.\n    assert count(\"hello ... world\") == {\"hello\": 1, \"world\": 1}\n\n\ndef test_internal_apostrophe_preserved():\n    assert count(\"don't can't don't\") == {\"don't\": 2, \"can't\": 1}\n\n\ndef test_mixed_case_and_punctuation():\n    out = count(\"Foo, BAR! foo? bar.\")\n    assert out == {\"foo\": 2, \"bar\": 2}\n"
          }
        ]
      }
    ],
    "rubric": {
      "items": [
        {
          "id": "correctness",
          "label": "Correctness",
          "weight": 0.5,
          "prompt": "Are all visible and hidden tests passing? Punctuation handling correct for the boundary cases?"
        },
        {
          "id": "code_quality",
          "label": "Code quality",
          "weight": 0.3,
          "prompt": "Is the punctuation logic readable and idiomatic? No regex if a stdlib helper suffices, no overengineering."
        },
        {
          "id": "verification_habits",
          "label": "Verification habits",
          "weight": 0.2,
          "prompt": "Did the candidate's chat history show probing/skepticism (e.g. asking about edge cases) before accepting the AI's first answer?"
        }
      ]
    },
    "topics": [
      "strings",
      "feature-add"
    ],
    "companies": [
      "Shopify",
      "Canva"
    ],
    "starter_files": [
      {
        "path": "wordcount.py",
        "contents": "\"\"\"Word-frequency counter.\n\nSpec:\n  count(text) returns a dict mapping each lowercased word to its\n  count. Words are split on whitespace, lowercased, then stripped of\n  any leading/trailing punctuation (use string.punctuation). Empty\n  tokens after stripping are NOT included in the result. Internal\n  characters (e.g. apostrophes in \"don't\") are preserved verbatim.\n\"\"\"\n\n\ndef count(text: str) -> dict[str, int]:\n    out: dict[str, int] = {}\n    for w in text.split():\n        key = w.lower()\n        out[key] = out.get(key, 0) + 1\n    return out\n"
      },
      {
        "path": "tests/checkpoint_0/test_visible.py",
        "contents": "from wordcount import count\n\n\n# These tests pass against the starter \u2014 they cover the\n# already-working baseline (whitespace split + lowercase). They stay\n# passing after the feature is added.\ndef test_basic_frequency():\n    assert count(\"hello world hello\") == {\"hello\": 2, \"world\": 1}\n\n\ndef test_lowercase_normalization():\n    assert count(\"Hello hello HELLO\") == {\"hello\": 3}\n\n\n# This test FAILS against the starter \u2014 it's the feature-add the\n# candidate must implement. The visible suite is intentionally red on\n# this entry until the work is done.\ndef test_strips_leading_and_trailing_punctuation():\n    assert count(\"hello, world! hello.\") == {\"hello\": 2, \"world\": 1}\n"
      }
    ]
  }
];

migrate(
  (db) => {
    const dao = new Dao(db);
    const coll = dao.findCollectionByNameOrId("ai_coding_rounds");
    for (const r of ROUNDS) {
      // Upsert: drop any existing row with this slug so the seed is
      // idempotent across re-applies (the previous strategy of
      // "skip on collision" left old rows with stale checkpoints).
      try {
        const old = dao.findFirstRecordByData("ai_coding_rounds", "slug", r.slug);
        dao.deleteRecord(old);
      } catch (_) { /* not present */ }
      const rec = new Record(coll, {
        slug: r.slug,
        title: r.title,
        difficulty: r.difficulty,
        language: r.language,
        description: r.description,
        starter_files: r.starter_files,
        checkpoints: r.checkpoints,
        rubric: r.rubric,
        topics: r.topics,
        companies: r.companies,
      });
      dao.saveRecord(rec);
    }
  },
  (db) => {
    const dao = new Dao(db);
    for (const r of ROUNDS) {
      try {
        const rec = dao.findFirstRecordByData("ai_coding_rounds", "slug", r.slug);
        dao.deleteRecord(rec);
      } catch (_) { /* ignore */ }
    }
  },
);
