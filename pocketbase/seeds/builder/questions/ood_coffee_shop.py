"""Coffee Shop Order System — Medium. Object-Oriented Design.

Domain modeling: Customer, Order, Employee, MenuItem. Strategy for
payment, observer for order-ready notifications, state machine for
order lifecycle."""
from builder.registry import register


PAYLOAD = {
    "title": "Coffee Shop Order System",
    "difficulty": "Medium",
    "description": (
        "Model a coffee shop order system. Required operations:\n"
        "- `add_to_menu(item_name, price_cents)` — add a menu item.\n"
        "- `place_order(customer_id, items)` — create a new order. Returns the order id. Items is a list "
        "of menu item names.\n"
        "- `mark_ready(order_id)` — transitions order from 'preparing' to 'ready'.\n"
        "- `pickup(order_id)` — transitions order from 'ready' to 'completed'. Only valid in 'ready' state.\n"
        "- `cancel(order_id)` — transitions order to 'cancelled'. Only valid in 'placed' or 'preparing'.\n"
        "- `total(order_id)` — returns the total price of the order in cents.\n"
        "- `status(order_id)` — returns the order's current state.\n\n"
        "Order states: `placed → preparing → ready → completed`, with `cancelled` reachable from any pre-"
        "ready state. The state transitions are STRICT — invalid transitions return `False` (`mark_ready`, "
        "`pickup`, `cancel`) without changing state."
    ),
    "hints": [
        "Domain objects: `MenuItem`, `Order`, `OrderState` (enum). Customer can be just an id for now — yes, premature.",
        "State machine: encode allowed transitions as a dict `state → set of allowed_next_states`. Each transition method consults the dict.",
        "Strategy pattern for payment, observer pattern for 'order ready' notifications — both are follow-ups, not v1.",
        "Don't return strings for state checks; use an enum (or string constant) consistently.",
        "Edge cases: place order with unknown menu item, mark_ready when not preparing, pickup when not ready, cancel when completed.",
    ],
    "constraints": [
        "1 <= total operations <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "class CoffeeShop:\n"
            "    def __init__(self): pass\n"
            "    def add_to_menu(self, item_name, price_cents): pass\n"
            "    def place_order(self, customer_id, items): pass\n"
            "    def mark_ready(self, order_id): pass\n"
            "    def pickup(self, order_id): pass\n"
            "    def cancel(self, order_id): pass\n"
            "    def total(self, order_id): pass\n"
            "    def status(self, order_id): pass"
        ),
        "javascript": (
            "class CoffeeShop {\n"
            "    constructor() {}\n"
            "    addToMenu(name, priceCents) {}\n"
            "    placeOrder(customerId, items) {}\n"
            "    markReady(orderId) {}\n"
            "    pickup(orderId) {}\n"
            "    cancel(orderId) {}\n"
            "    total(orderId) {}\n"
            "    status(orderId) {}\n"
            "}"
        ),
        "java": (
            "class CoffeeShop {\n"
            "    public CoffeeShop() {}\n"
            "    public void addToMenu(String name, int priceCents) {}\n"
            "    public Integer placeOrder(String customerId, List<String> items) { return null; }\n"
            "    public boolean markReady(int orderId) { return false; }\n"
            "    public boolean pickup(int orderId) { return false; }\n"
            "    public boolean cancel(int orderId) { return false; }\n"
            "    public Integer total(int orderId) { return null; }\n"
            "    public String status(int orderId) { return null; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    s = CoffeeShop()\n"
            "    s.add_to_menu('latte', 500)\n"
            "    oid = s.place_order('alice', ['latte'])\n"
            "    print(s.total(oid), s.status(oid))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["CoffeeShop", "add_to_menu", "place_order", "total", "status"],
                    "args": [[], ["latte", 500], ["alice", ["latte"]], [1], [1]]},
         "expected": [None, None, 1, 500, "placed"],
         "description": "Add menu, place, check total + status", "tags": ["basic"]},
        {"input": {"ops": ["CoffeeShop", "add_to_menu", "add_to_menu", "place_order", "total"],
                    "args": [[], ["latte", 500], ["muffin", 300], ["bob", ["latte", "muffin", "latte"]], [1]]},
         "expected": [None, None, None, 1, 1300],
         "description": "Multi-item order; total is sum", "tags": ["basic"]},
        {"input": {"ops": ["CoffeeShop", "add_to_menu", "place_order",
                            "mark_ready", "pickup", "status"],
                    "args": [[], ["latte", 500], ["alice", ["latte"]], [1], [1], [1]]},
         "expected": [None, None, 1, True, True, "completed"],
         "description": "Happy path: placed → ready → completed", "tags": ["basic"]},
        {"input": {"ops": ["CoffeeShop", "add_to_menu", "place_order", "pickup"],
                    "args": [[], ["latte", 500], ["a", ["latte"]], [1]]},
         "expected": [None, None, 1, False],
         "description": "Pickup before ready is rejected", "tags": ["edge"]},
        {"input": {"ops": ["CoffeeShop", "add_to_menu", "place_order",
                            "cancel", "mark_ready", "status"],
                    "args": [[], ["latte", 500], ["a", ["latte"]], [1], [1], [1]]},
         "expected": [None, None, 1, True, False, "cancelled"],
         "description": "Cancel terminates; mark_ready post-cancel rejected",
         "tags": ["edge"]},
        {"input": {"ops": ["CoffeeShop", "place_order"],
                    "args": [[], ["a", ["unknown"]]]},
         "expected": [None, None],
         "description": "Unknown menu item — order rejected (returns None)",
         "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "State-Machine OOD (Optimal)",
            "time_complexity": "O(1) per op",
            "space_complexity": "O(N) orders + O(M) menu",
            "description": (
                "Domain objects: MenuItem (name, price), Order (id, customer, items, state). State "
                "transitions are governed by a dict mapping each state to its allowed next states. "
                "Each transition method is a one-liner that consults the dict and updates."
            ),
            "code": {
                "python": (
                    "class CoffeeShop:\n"
                    "    _NEXT = {\n"
                    "        'placed':     {'preparing', 'cancelled'},\n"
                    "        'preparing':  {'ready', 'cancelled'},\n"
                    "        'ready':      {'completed'},\n"
                    "        'completed':  set(),\n"
                    "        'cancelled':  set(),\n"
                    "    }\n"
                    "    def __init__(self):\n"
                    "        self._menu = {}\n"
                    "        self._orders = {}\n"
                    "        self._next_id = 1\n"
                    "    def add_to_menu(self, name, price_cents):\n"
                    "        self._menu[name] = price_cents\n"
                    "    def place_order(self, customer_id, items):\n"
                    "        if any(i not in self._menu for i in items):\n"
                    "            return None\n"
                    "        oid = self._next_id; self._next_id += 1\n"
                    "        self._orders[oid] = {'customer': customer_id, 'items': list(items),\n"
                    "                              'state': 'placed'}\n"
                    "        return oid\n"
                    "    def _transition(self, oid, target):\n"
                    "        if oid not in self._orders: return False\n"
                    "        cur = self._orders[oid]['state']\n"
                    "        if target not in self._NEXT[cur]: return False\n"
                    "        self._orders[oid]['state'] = target\n"
                    "        return True\n"
                    "    def mark_ready(self, oid):\n"
                    "        if oid not in self._orders: return False\n"
                    "        # placed → preparing → ready, allow direct placed → ready too if you want\n"
                    "        cur = self._orders[oid]['state']\n"
                    "        if cur == 'placed':\n"
                    "            self._orders[oid]['state'] = 'preparing'\n"
                    "        return self._transition(oid, 'ready')\n"
                    "    def pickup(self, oid):\n"
                    "        return self._transition(oid, 'completed')\n"
                    "    def cancel(self, oid):\n"
                    "        return self._transition(oid, 'cancelled')\n"
                    "    def total(self, oid):\n"
                    "        if oid not in self._orders: return None\n"
                    "        return sum(self._menu[i] for i in self._orders[oid]['items'])\n"
                    "    def status(self, oid):\n"
                    "        return self._orders[oid]['state'] if oid in self._orders else None"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Domain objects first: MenuItem, Order, Customer (just an id at v1).",
        "2. State machine: enumerate states (placed, preparing, ready, completed, cancelled). Encode allowed transitions in a dict.",
        "3. Each transition method validates against the dict; refuses on disallowed transitions.",
        "4. total: walk the order's items, sum prices from the menu.",
        "5. Strategy pattern for payment is a v2 follow-up. Same with observer for ready-notifications and ordering channel (mobile vs walk-in).",
        "6. Edge cases: invalid transitions, unknown order id, order with unknown item, transitions from cancelled or completed (always rejected).",
    ],
    "tips": [
        "Don't put state-transition logic INSIDE the Order class as a 1000-line method. The dict-of-allowed-transitions pattern decouples enumeration from logic.",
        "Strategy for payment lets you add Cash, CreditCard, MobileWallet without touching Order.",
        "Observer for 'order ready' lets the customer's app subscribe; in v1 it's just a list of subscribers.",
        "Common follow-up: 'channel tracking' — order via mobile vs drive-thru vs cashier. Add a field; pass it through. Keep payment/notification orthogonal.",
        "Common follow-up: 'tipping.' Either a separate field on Order or a special MenuItem ('tip', price=0); each has trade-offs.",
    ],
    "companies": ["Amazon", "Square", "Starbucks"],
    "topics": ["Object-Oriented Design", "State Machine", "Strategy Pattern"],
    "time_complexity": "O(1) per op",
    "space_complexity": "O(N + M)",
}


def REFERENCE(input):
    class CoffeeShop:
        _NEXT = {
            "placed": {"preparing", "cancelled"},
            "preparing": {"ready", "cancelled"},
            "ready": {"completed"},
            "completed": set(),
            "cancelled": set(),
        }

        def __init__(self):
            self._menu = {}
            self._orders = {}
            self._next_id = 1

        def add_to_menu(self, name, price_cents):
            self._menu[name] = price_cents

        def place_order(self, customer_id, items):
            if any(i not in self._menu for i in items):
                return None
            oid = self._next_id
            self._next_id += 1
            self._orders[oid] = {
                "customer": customer_id,
                "items": list(items),
                "state": "placed",
            }
            return oid

        def _transition(self, oid, target):
            if oid not in self._orders:
                return False
            cur = self._orders[oid]["state"]
            if target not in self._NEXT[cur]:
                return False
            self._orders[oid]["state"] = target
            return True

        def mark_ready(self, oid):
            if oid not in self._orders:
                return False
            cur = self._orders[oid]["state"]
            if cur == "placed":
                self._orders[oid]["state"] = "preparing"
            return self._transition(oid, "ready")

        def pickup(self, oid):
            return self._transition(oid, "completed")

        def cancel(self, oid):
            return self._transition(oid, "cancelled")

        def total(self, oid):
            if oid not in self._orders:
                return None
            return sum(self._menu[i] for i in self._orders[oid]["items"])

        def status(self, oid):
            return self._orders[oid]["state"] if oid in self._orders else None

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "CoffeeShop":
            instance = CoffeeShop()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "CoffeeShop",
    "constructor": {"params": []},
    "methods": [
        {"name": "add_to_menu", "params": [
            {"name": "item_name", "type": "string"},
            {"name": "price_cents", "type": "int"},
        ], "returns": "any"},
        {"name": "place_order", "params": [
            {"name": "customer_id", "type": "string"},
            {"name": "items", "type": "string[]"},
        ], "returns": "any"},
        {"name": "mark_ready", "params": [{"name": "order_id", "type": "int"}], "returns": "bool"},
        {"name": "pickup", "params": [{"name": "order_id", "type": "int"}], "returns": "bool"},
        {"name": "cancel", "params": [{"name": "order_id", "type": "int"}], "returns": "bool"},
        {"name": "total", "params": [{"name": "order_id", "type": "int"}], "returns": "any"},
        {"name": "status", "params": [{"name": "order_id", "type": "int"}], "returns": "any"},
    ],
}


register(PAYLOAD, REFERENCE)
