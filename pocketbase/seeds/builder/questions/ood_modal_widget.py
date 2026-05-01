"""Modal Widget — Easy/Medium. OOD / Frontend domain.

Model the API surface of a Modal component without the DOM. Open/close
state, content loaders (for async-loaded titles+bodies), event handlers
(close on Escape / outside-click), accessibility focus management."""
from builder.registry import register


PAYLOAD = {
    "title": "Modal Widget Component (Domain Model)",
    "difficulty": "Medium",
    "description": (
        "Implement the **state model** for a Modal widget component (no actual DOM — this is the "
        "headless logic). Required operations:\n"
        "- `register_button(button_id, content_url)` — register a trigger button with the URL its content "
        "is loaded from.\n"
        "- `click(button_id, fetch_response)` — simulate a button click. `fetch_response` is the "
        "content the harness pretends the network returns (`None` to simulate a network error). On "
        "success, the modal opens with that content. On error, the modal does NOT open and the error is "
        "recorded.\n"
        "- `close()` — close the modal.\n"
        "- `escape_pressed()` — equivalent to close (for keyboard accessibility).\n"
        "- `outside_click()` — equivalent to close (for click-outside dismissal).\n"
        "- `state()` — returns dict `{open: bool, content: str|None, last_error: str|None, button: id|None}`.\n\n"
        "**Caching:** if a button is clicked again, the cached content is used; the harness's "
        "`fetch_response` for cached buttons is ignored. The cache should be per-button, persisting across "
        "modal opens and closes."
    ),
    "hints": [
        "State: `is_open`, `content`, `last_error`, `current_button`. Plus a `cache: button_id → content` map.",
        "click flow: cached → open immediately. Not cached → use fetch_response (may be None for error).",
        "Caching is the senior signal — don't refetch known content on repeat opens.",
        "Escape / outside-click are just close aliases — don't duplicate close logic.",
        "Accessibility hint: when modal opens, save 'previously focused element'; on close, restore. We don't model focus here, but mention it.",
        "Edge cases: click on unregistered button (no-op), close when not open (no-op), fetch_response is None (error path).",
    ],
    "constraints": [
        "1 <= total operations <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "class Modal:\n"
            "    def __init__(self): pass\n"
            "    def register_button(self, button_id, content_url): pass\n"
            "    def click(self, button_id, fetch_response): pass\n"
            "    def close(self): pass\n"
            "    def escape_pressed(self): pass\n"
            "    def outside_click(self): pass\n"
            "    def state(self): pass"
        ),
        "javascript": (
            "class Modal {\n"
            "    constructor() {}\n"
            "    registerButton(id, url) {}\n"
            "    click(id, response) {}\n"
            "    close() {}\n"
            "    escapePressed() {}\n"
            "    outsideClick() {}\n"
            "    state() {}\n"
            "}"
        ),
        "java": (
            "class Modal {\n"
            "    public Modal() {}\n"
            "    public void registerButton(String id, String url) {}\n"
            "    public void click(String id, String response) {}\n"
            "    public void close() {}\n"
            "    public void escapePressed() {}\n"
            "    public void outsideClick() {}\n"
            "    public Map<String,Object> state() { return new HashMap<>(); }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    m = Modal()\n"
            "    m.register_button('B1', '/api/b1')\n"
            "    m.click('B1', 'Hello')\n"
            "    print(m.state())"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["Modal", "register_button", "click", "state"],
                    "args": [[], ["B1", "/api/b1"], ["B1", "Hello"], []]},
         "expected": [None, None, None,
                       {"open": True, "content": "Hello", "last_error": None, "button": "B1"}],
         "description": "Click opens with content", "tags": ["basic"]},
        {"input": {"ops": ["Modal", "register_button", "click", "close", "state"],
                    "args": [[], ["B1", "/api/b1"], ["B1", "Hello"], [], []]},
         "expected": [None, None, None, None,
                       {"open": False, "content": None, "last_error": None, "button": None}],
         "description": "Close clears state", "tags": ["basic"]},
        {"input": {"ops": ["Modal", "register_button", "click", "close", "click", "state"],
                    "args": [[], ["B1", "/api/b1"], ["B1", "First"], [], ["B1", "Second"], []]},
         "expected": [None, None, None, None, None,
                       {"open": True, "content": "First", "last_error": None, "button": "B1"}],
         "description": "Cached content used on second click — 'Second' ignored",
         "tags": ["tricky"]},
        {"input": {"ops": ["Modal", "register_button", "click", "state"],
                    "args": [[], ["B1", "/api/b1"], ["B1", None], []]},
         "expected": [None, None, None,
                       {"open": False, "content": None, "last_error": "fetch_failed", "button": None}],
         "description": "Network error keeps modal closed", "tags": ["edge"]},
        {"input": {"ops": ["Modal", "click", "state"],
                    "args": [[], ["B1", "X"], []]},
         "expected": [None, None,
                       {"open": False, "content": None, "last_error": None, "button": None}],
         "description": "Click on unregistered button — no-op", "tags": ["edge"]},
        {"input": {"ops": ["Modal", "register_button", "click", "escape_pressed", "state"],
                    "args": [[], ["B1", "/api/b1"], ["B1", "X"], [], []]},
         "expected": [None, None, None, None,
                       {"open": False, "content": None, "last_error": None, "button": None}],
         "description": "Escape closes the modal", "tags": ["basic"]},
        {"input": {"ops": ["Modal", "register_button", "click", "outside_click", "state"],
                    "args": [[], ["B1", "/api/b1"], ["B1", "X"], [], []]},
         "expected": [None, None, None, None,
                       {"open": False, "content": None, "last_error": None, "button": None}],
         "description": "Outside-click closes the modal", "tags": ["basic"]},
    ],
    "solutions": [
        {
            "title": "Plain State + Cache (Optimal)",
            "time_complexity": "O(1) per op",
            "space_complexity": "O(N) cache",
            "description": (
                "Top-level fields for is_open, content, last_error, current_button. Cache map keyed by "
                "button id. click flow: registered? cached? fetch_response valid? Open or record error."
            ),
            "code": {
                "python": (
                    "class Modal:\n"
                    "    def __init__(self):\n"
                    "        self._buttons = {}\n"
                    "        self._cache = {}\n"
                    "        self._open = False\n"
                    "        self._content = None\n"
                    "        self._last_error = None\n"
                    "        self._button = None\n"
                    "    def register_button(self, button_id, content_url):\n"
                    "        self._buttons[button_id] = content_url\n"
                    "    def click(self, button_id, fetch_response):\n"
                    "        if button_id not in self._buttons:\n"
                    "            return\n"
                    "        if button_id in self._cache:\n"
                    "            self._open = True; self._button = button_id\n"
                    "            self._content = self._cache[button_id]\n"
                    "            self._last_error = None\n"
                    "            return\n"
                    "        if fetch_response is None:\n"
                    "            self._last_error = 'fetch_failed'\n"
                    "            return\n"
                    "        self._cache[button_id] = fetch_response\n"
                    "        self._open = True; self._button = button_id\n"
                    "        self._content = fetch_response; self._last_error = None\n"
                    "    def close(self):\n"
                    "        self._open = False; self._content = None; self._button = None\n"
                    "    escape_pressed = close\n"
                    "    outside_click = close\n"
                    "    def state(self):\n"
                    "        return {'open': self._open, 'content': self._content,\n"
                    "                'last_error': self._last_error, 'button': self._button}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. State pieces: is_open, content, last_error, current_button. Plus per-button cache.",
        "2. click flow: not registered → no-op. Cached → use cache. Else → use fetch_response (None means error).",
        "3. close clears the open state but NOT the cache (cache persists for future clicks).",
        "4. escape_pressed and outside_click are aliases for close — don't write three implementations.",
        "5. Mention in the discussion: in real code, focus management (save+restore) and ARIA attributes are part of the API. Out of scope for this question's testable surface.",
        "6. Edge cases: unregistered button click, fetch error, repeat clicks (cache hit), close when not open.",
    ],
    "tips": [
        "Don't write three close methods; write one and alias.",
        "Cache key is the button id, not the URL — even if multiple buttons share a URL, each gets its own cache entry by spec.",
        "Common follow-up: 'cache invalidation.' TTL per cache entry, or explicit refresh API.",
        "Common follow-up: 'multiple modals open at once.' Stack of open modals; close pops the top. Esc closes the topmost.",
        "Common follow-up: 'integrate with React.' This headless model BECOMES a hook (`useModal`) — the same state machine drives the UI.",
    ],
    "companies": ["Amazon", "Microsoft", "Google"],
    "topics": ["Object-Oriented Design", "State Management", "UI Components"],
    "time_complexity": "O(1) per op",
    "space_complexity": "O(N) cache",
}


def REFERENCE(input):
    class Modal:
        def __init__(self):
            self._buttons = {}
            self._cache = {}
            self._open = False
            self._content = None
            self._last_error = None
            self._button = None

        def register_button(self, button_id, content_url):
            self._buttons[button_id] = content_url

        def click(self, button_id, fetch_response):
            if button_id not in self._buttons:
                return
            if button_id in self._cache:
                self._open = True
                self._button = button_id
                self._content = self._cache[button_id]
                self._last_error = None
                return
            if fetch_response is None:
                self._last_error = "fetch_failed"
                return
            self._cache[button_id] = fetch_response
            self._open = True
            self._button = button_id
            self._content = fetch_response
            self._last_error = None

        def close(self):
            self._open = False
            self._content = None
            self._button = None

        def escape_pressed(self):
            self.close()

        def outside_click(self):
            self.close()

        def state(self):
            return {
                "open": self._open,
                "content": self._content,
                "last_error": self._last_error,
                "button": self._button,
            }

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "Modal":
            instance = Modal()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "Modal",
    "constructor": {"params": []},
    "methods": [
        {"name": "register_button", "params": [
            {"name": "button_id", "type": "string"},
            {"name": "content_url", "type": "string"},
        ], "returns": "any"},
        {"name": "click", "params": [
            {"name": "button_id", "type": "string"},
            {"name": "fetch_response", "type": "any"},
        ], "returns": "any"},
        {"name": "close", "params": [], "returns": "any"},
        {"name": "escape_pressed", "params": [], "returns": "any"},
        {"name": "outside_click", "params": [], "returns": "any"},
        {"name": "state", "params": [], "returns": "any"},
    ],
}


register(PAYLOAD, REFERENCE)
