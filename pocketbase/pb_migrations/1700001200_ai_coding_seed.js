/// <reference path="../pb_data/types.d.ts" />

const ROUNDS = [
  {
    "slug": "hallucinated-http-client",
    "title": "Hallucinated HTTP client method",
    "difficulty": "easy",
    "languages": [
      "python",
      "typescript"
    ],
    "topics": [
      "ai-output-review",
      "http-client",
      "library-knowledge"
    ],
    "companies": [
      "Meta",
      "Shopify"
    ],
    "description": "An AI assistant wrote a small function that fetches a JSON payload from an internal service. The visible test passes against a stub. Find what's wrong before it ships against the real service.\n\nThis is an **audit** round. The AI's draft compiles and the visible test passes \u2014 but the code calls a method that doesn't exist on the chosen HTTP library. Your job is to spot the hallucination, replace it with the correct API, and preserve the function's signature and behavior contract.\n\nTen minutes is plenty if you read the AI output critically. If you only run the visible test and ship, you'll ship a 500.",
    "rubric": {
      "items": [
        {
          "id": "spotted_hallucination",
          "label": "Spotted the hallucination",
          "weight": 0.4,
          "prompt": "Did the candidate identify that the AI-generated call (httpx.get_json / fetch.json) doesn't exist on the real library, rather than trusting that the visible test implied correctness?"
        },
        {
          "id": "minimal_correct_fix",
          "label": "Minimal, correct fix",
          "weight": 0.3,
          "prompt": "Did the candidate make a minimal change \u2014 replace the bogus call with the real API (httpx.get(...).json() / fetch(...).then(r => r.json())) \u2014 without rewriting the function from scratch or changing its signature?"
        },
        {
          "id": "verification_habits",
          "label": "Verification habits",
          "weight": 0.2,
          "prompt": "Examining the chat history: did the candidate cross-check the AI's suggestion against documentation or first-principles library knowledge before accepting it? Or did they accept the AI's reassurance at face value?"
        },
        {
          "id": "test_critique",
          "label": "Test critique",
          "weight": 0.1,
          "prompt": "Did the candidate articulate why the visible test was insufficient \u2014 specifically, that mocking a method by name with create=True (Python) or by assignment (TS) creates the attribute and masks its absence on the real library?"
        }
      ]
    },
    "language": "python",
    "starter_files": {
      "python": [
        {
          "path": "client.py",
          "contents": "\"\"\"Fetch a user profile from the internal users service.\n\nAn AI assistant wrote this file. The visible test passes, so it's ready\nto ship \u2014 but it has not yet been pointed at the real service.\n\"\"\"\nimport httpx\n\n\nINTERNAL_BASE_URL = \"http://internal-users.local\"\n\n\ndef fetch_user(user_id: str) -> dict:\n    \"\"\"Return the JSON body of GET /users/{user_id} as a dict.\n\n    Raises:\n        RuntimeError: if the upstream returns a non-2xx response.\n    \"\"\"\n    url = f\"{INTERNAL_BASE_URL}/users/{user_id}\"\n    # `httpx.get_json` is the friendly wrapper \u2014 it folds the\n    # `.json()` step in and raises on non-2xx automatically. The AI\n    # said this is the idiomatic way to do it.\n    return httpx.get_json(url, timeout=5.0)\n"
        },
        {
          "path": "tests/checkpoint_0/test_visible.py",
          "contents": "\"\"\"Visible test \u2014 passes against a mock. Stands in for BOTH the AI's\ninvented method AND the real `httpx.get(...).json()` combo so either\nimplementation passes here. That's exactly why the hidden test is\nneeded against a real server \u2014 the visible test alone cannot catch\nthe hallucination.\"\"\"\nfrom unittest.mock import MagicMock, patch\n\nimport client\n\n\ndef _mock_response(payload):\n    r = MagicMock()\n    r.json.return_value = payload\n    r.raise_for_status.return_value = None\n    r.status_code = 200\n    return r\n\n\ndef test_fetch_user_returns_dict():\n    expected = {\"id\": \"u-1\", \"name\": \"Alex\"}\n    with patch.object(client.httpx, \"get\", return_value=_mock_response(expected)), \\\n         patch.object(client.httpx, \"get_json\", return_value=expected, create=True):\n        result = client.fetch_user(\"u-1\")\n    assert result == expected\n"
        }
      ],
      "typescript": [
        {
          "path": "client.ts",
          "contents": "/**\n * Fetch a user profile from the internal users service.\n *\n * An AI assistant wrote this file. The visible test passes, so it's\n * ready to ship \u2014 but it has not yet been pointed at the real service.\n */\n\n// Mutable so tests/integration code can repoint the URL at a local\n// server without rebuilding. In production, prefer environment-based\n// configuration.\nexport const config = {\n  baseUrl: 'http://internal-users.local',\n};\n\nexport interface UserProfile {\n  id: string;\n  name: string;\n}\n\nexport async function fetchUser(userId: string): Promise<UserProfile> {\n  const url = `${config.baseUrl}/users/${userId}`;\n  // `fetch.json` is the friendly wrapper \u2014 it folds the `.json()`\n  // step in and raises on non-2xx automatically. The AI said this\n  // is the idiomatic way to do it.\n  return (fetch as any).json(url, { timeout: 5000 });\n}\n"
        },
        {
          "path": "tests/checkpoint_0/client.test.ts",
          "contents": "import { test } from 'node:test';\nimport assert from 'node:assert/strict';\n\nimport { fetchUser } from '../../client.ts';\n\ntest('fetchUser returns the JSON body', async () => {\n  const expected = { id: 'u-1', name: 'Alex' };\n\n  // Stand in for both the AI's invented method AND the real\n  // `fetch(...).json()` combo so either implementation passes here.\n  // That's exactly why the hidden test is needed against a real\n  // server \u2014 the visible test alone cannot catch the hallucination.\n  const fakeFetch: any = async () => ({\n    ok: true,\n    status: 200,\n    json: async () => expected,\n  });\n  fakeFetch.json = async () => expected;\n\n  const originalFetch = globalThis.fetch;\n  globalThis.fetch = fakeFetch;\n  try {\n    const result = await fetchUser('u-1');\n    assert.deepEqual(result, expected);\n  } finally {\n    globalThis.fetch = originalFetch;\n  }\n});\n"
        }
      ]
    },
    "checkpoints": {
      "python": [
        {
          "label": "Spot the hallucinated call",
          "prompt": "Read `client.py`. The visible test in `tests/checkpoint_0/test_visible.py` passes. Find what's wrong before this ships against the real internal-users service, then fix `client.py` so it would also work against a real HTTP server.\n\nKeep the public signature of `fetch_user(user_id: str) -> dict` unchanged. Don't rewrite from scratch \u2014 the bug is one call.",
          "ai_allowed": true,
          "test_command": "pytest tests/checkpoint_0/test_visible.py -q",
          "tests_glob": "tests/**/*.py",
          "hidden_files": [
            {
              "path": "tests/checkpoint_0/test_hidden.py",
              "contents": "\"\"\"Hidden test \u2014 exercises fetch_user against a real local HTTP server.\nA solution that still calls `httpx.get_json` raises AttributeError at\nimport-time exercise, because that method does not exist on the real\nlibrary. The visible mock-based test cannot catch this.\"\"\"\nimport json\nimport threading\nfrom http.server import BaseHTTPRequestHandler, HTTPServer\n\nimport pytest\n\nimport client\n\n\nclass _Handler(BaseHTTPRequestHandler):\n    def do_GET(self):\n        if self.path.startswith(\"/users/\"):\n            user_id = self.path.removeprefix(\"/users/\")\n            body = json.dumps({\"id\": user_id, \"name\": \"Real\"}).encode()\n            self.send_response(200)\n            self.send_header(\"Content-Type\", \"application/json\")\n            self.send_header(\"Content-Length\", str(len(body)))\n            self.end_headers()\n            self.wfile.write(body)\n        else:\n            self.send_response(404)\n            self.end_headers()\n\n    def log_message(self, *_args, **_kwargs):\n        pass\n\n\n@pytest.fixture(scope=\"module\")\ndef server():\n    httpd = HTTPServer((\"127.0.0.1\", 0), _Handler)\n    port = httpd.server_address[1]\n    t = threading.Thread(target=httpd.serve_forever, daemon=True)\n    t.start()\n    yield f\"http://127.0.0.1:{port}\"\n    httpd.shutdown()\n    httpd.server_close()\n\n\ndef test_fetch_user_against_real_server(server, monkeypatch):\n    monkeypatch.setattr(client, \"INTERNAL_BASE_URL\", server)\n    result = client.fetch_user(\"u-42\")\n    assert result == {\"id\": \"u-42\", \"name\": \"Real\"}\n"
            }
          ]
        }
      ],
      "typescript": [
        {
          "label": "Spot the hallucinated call",
          "prompt": "Read `client.ts`. The visible test in `tests/checkpoint_0/client.test.ts` passes. Find what's wrong before this ships against the real internal-users service, then fix `client.ts` so it would also work against a real HTTP server.\n\nKeep the public signature of `fetchUser(userId: string): Promise<UserProfile>` unchanged. Don't rewrite from scratch \u2014 the bug is one call.",
          "ai_allowed": true,
          "test_command": "tsx --test tests/checkpoint_0/client.test.ts",
          "tests_glob": "tests/**/*.ts",
          "hidden_files": [
            {
              "path": "tests/checkpoint_0/client.test.ts",
              "contents": "import { test, before, after } from 'node:test';\nimport assert from 'node:assert/strict';\nimport { createServer, type Server } from 'node:http';\n\nimport { fetchUser, config } from '../../client.ts';\n\nlet server: Server;\nlet baseUrl: string;\n\nbefore(async () => {\n  server = createServer((req, res) => {\n    if (req.url?.startsWith('/users/')) {\n      const id = req.url.replace('/users/', '');\n      res.statusCode = 200;\n      res.setHeader('Content-Type', 'application/json');\n      res.end(JSON.stringify({ id, name: 'Real' }));\n    } else {\n      res.statusCode = 404;\n      res.end();\n    }\n  });\n  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', () => resolve()));\n  const addr = server.address();\n  baseUrl =\n    typeof addr === 'object' && addr ? `http://127.0.0.1:${addr.port}` : '';\n  config.baseUrl = baseUrl;\n});\n\nafter(async () => {\n  await new Promise<void>((resolve) => server.close(() => resolve()));\n});\n\ntest('fetchUser against real server', async () => {\n  const result = await fetchUser('u-42');\n  assert.deepEqual(result, { id: 'u-42', name: 'Real' });\n});\n"
            }
          ]
        }
      ]
    }
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
        // For multi-language rounds `language` is the primary (first
        // entry of manifest.languages); the full set is derivable from
        // Object.keys(checkpoints) when checkpoints is a map.
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
