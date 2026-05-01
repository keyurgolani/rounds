"""Vending Machine — Medium. Object-Oriented Design / State Machine.

States: idle → has_money → dispensing → idle. Restock and inventory
checks. Bar-raise: locale support and configurable item options."""
from builder.registry import register


PAYLOAD = {
    "title": "Vending Machine",
    "difficulty": "Medium",
    "description": (
        "Model a vending machine. Operations:\n"
        "- `restock(item_id, name, price_cents, count)` — adds (or replenishes) an item slot.\n"
        "- `insert_money(amount_cents)` — adds money to the inserted-amount counter.\n"
        "- `select(item_id)` — attempts to dispense `item_id`. Returns one of `'ok'` (success — decrement "
        "stock, decrement money by price, return change), `'insufficient_funds'`, `'out_of_stock'`, "
        "`'unknown_item'`.\n"
        "- `refund()` — returns currently inserted amount and resets to 0.\n"
        "- `inventory(item_id)` — returns the current stock count, or None if unknown.\n"
        "- `change_due()` — returns the change owed since the last successful select (returned by that "
        "`select` call as the integer cents owed; this method just returns the most recent value, or 0).\n\n"
        "After a successful select, the inserted amount drops by the item's price; any excess becomes the "
        "change due."
    ),
    "hints": [
        "Domain: Item (id, name, price, count), VendingMachine (inventory dict, inserted, last_change_due).",
        "State is implicit in `inserted` and `last_change_due`. Don't over-engineer it into a state-machine class for the v1.",
        "select returns a string code. Tuple `(code, change_due)` is the bar-raising shape — but keep the API simple per the spec.",
        "Locale follow-up: pull price formatting and currency handling into a Locale strategy. Don't hardcode '$'.",
        "Refund is independent of selection — refund-while-inserted returns the inserted amount; resets state.",
        "Edge cases: select with no money inserted, select on out-of-stock, refund with nothing inserted, restock with count=0.",
    ],
    "constraints": [
        "1 <= total operations <= 10⁴",
    ],
    "starter_code": {
        "python": (
            "class VendingMachine:\n"
            "    def __init__(self): pass\n"
            "    def restock(self, item_id, name, price_cents, count): pass\n"
            "    def insert_money(self, amount_cents): pass\n"
            "    def select(self, item_id): pass\n"
            "    def refund(self): pass\n"
            "    def inventory(self, item_id): pass\n"
            "    def change_due(self): pass"
        ),
        "javascript": (
            "class VendingMachine {\n"
            "    constructor() {}\n"
            "    restock(id, name, price, count) {}\n"
            "    insertMoney(amount) {}\n"
            "    select(id) {}\n"
            "    refund() {}\n"
            "    inventory(id) {}\n"
            "    changeDue() {}\n"
            "}"
        ),
        "java": (
            "class VendingMachine {\n"
            "    public VendingMachine() {}\n"
            "    public void restock(String id, String name, int price, int count) {}\n"
            "    public void insertMoney(int amount) {}\n"
            "    public String select(String id) { return null; }\n"
            "    public int refund() { return 0; }\n"
            "    public Integer inventory(String id) { return null; }\n"
            "    public int changeDue() { return 0; }\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    vm = VendingMachine()\n"
            "    vm.restock('A1', 'Coke', 150, 5)\n"
            "    vm.insert_money(200)\n"
            "    print(vm.select('A1'))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"ops": ["VendingMachine", "restock", "insert_money", "select",
                            "change_due", "inventory"],
                    "args": [[], ["A1", "Coke", 150, 5], [200], ["A1"], [], ["A1"]]},
         "expected": [None, None, None, "ok", 50, 4],
         "description": "Insert 200, buy 150 — change 50, stock down to 4",
         "tags": ["basic"]},
        {"input": {"ops": ["VendingMachine", "restock", "insert_money", "select"],
                    "args": [[], ["A1", "Coke", 150, 5], [100], ["A1"]]},
         "expected": [None, None, None, "insufficient_funds"],
         "description": "Not enough money", "tags": ["edge"]},
        {"input": {"ops": ["VendingMachine", "restock", "insert_money", "select"],
                    "args": [[], ["A1", "Coke", 150, 0], [200], ["A1"]]},
         "expected": [None, None, None, "out_of_stock"],
         "description": "Restocked with 0 — out of stock", "tags": ["edge"]},
        {"input": {"ops": ["VendingMachine", "insert_money", "select"],
                    "args": [[], [200], ["X1"]]},
         "expected": [None, None, "unknown_item"],
         "description": "Unknown item id", "tags": ["edge"]},
        {"input": {"ops": ["VendingMachine", "insert_money", "insert_money", "refund"],
                    "args": [[], [50], [75], []]},
         "expected": [None, None, None, 125],
         "description": "Refund returns total inserted", "tags": ["basic"]},
        {"input": {"ops": ["VendingMachine", "restock", "restock", "inventory"],
                    "args": [[], ["A1", "X", 100, 3], ["A1", "X", 100, 5], ["A1"]]},
         "expected": [None, None, None, 8],
         "description": "Restock adds to existing count", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Domain Model with String Codes (Optimal)",
            "time_complexity": "O(1) per op",
            "space_complexity": "O(N) items",
            "description": (
                "Item dict keyed by id. Inserted amount is a single counter. select() validates "
                "(unknown, out-of-stock, funds), updates state, returns a code. Last change due is stored "
                "for the change_due() query."
            ),
            "code": {
                "python": (
                    "class VendingMachine:\n"
                    "    def __init__(self):\n"
                    "        self._items = {}\n"
                    "        self._inserted = 0\n"
                    "        self._last_change = 0\n"
                    "    def restock(self, item_id, name, price_cents, count):\n"
                    "        if item_id in self._items:\n"
                    "            self._items[item_id]['count'] += count\n"
                    "        else:\n"
                    "            self._items[item_id] = {'name': name, 'price': price_cents, 'count': count}\n"
                    "    def insert_money(self, amount_cents):\n"
                    "        self._inserted += amount_cents\n"
                    "    def select(self, item_id):\n"
                    "        item = self._items.get(item_id)\n"
                    "        if item is None:\n"
                    "            return 'unknown_item'\n"
                    "        if item['count'] <= 0:\n"
                    "            return 'out_of_stock'\n"
                    "        if self._inserted < item['price']:\n"
                    "            return 'insufficient_funds'\n"
                    "        self._inserted -= item['price']\n"
                    "        self._last_change = self._inserted\n"
                    "        self._inserted = 0\n"
                    "        item['count'] -= 1\n"
                    "        return 'ok'\n"
                    "    def refund(self):\n"
                    "        amt = self._inserted\n"
                    "        self._inserted = 0\n"
                    "        return amt\n"
                    "    def inventory(self, item_id):\n"
                    "        return self._items[item_id]['count'] if item_id in self._items else None\n"
                    "    def change_due(self):\n"
                    "        return self._last_change"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Domain objects: Item, VendingMachine. Customer is implicit.",
        "2. select() is the state-changing method — handle unknown / out-of-stock / insufficient as separate cases. Don't merge.",
        "3. Inserted amount is a single counter; reset on success, returned on refund.",
        "4. Restock semantics: add to existing count if item exists; else create.",
        "5. Locale follow-up: pull formatting into a Locale strategy. Don't hardcode '$'.",
        "6. Edge cases: insufficient funds, out-of-stock, unknown item, refund-while-empty, restock count=0.",
    ],
    "tips": [
        "Don't bake real currency formatting into the model — that's a view concern. Cents-as-int is the only money representation that doesn't accumulate float errors.",
        "If you find yourself with `if currency == 'JPY'` branches, you've missed the strategy. Locale handler decides display + rounding.",
        "Common follow-up: 'coffee with milk/sugar choices.' Decorator pattern on the base coffee item; price rolls up.",
        "Common follow-up: 'audit log.' Each transaction emits an event; subscribe a logger.",
        "Common follow-up: 'concurrency.' Lock the inventory map per item; insert/refund per-machine lock.",
    ],
    "companies": ["Amazon", "Coca-Cola IT", "Bloomberg"],
    "topics": ["Object-Oriented Design", "State Machine"],
    "time_complexity": "O(1) per op",
    "space_complexity": "O(N)",
}


def REFERENCE(input):
    class VendingMachine:
        def __init__(self):
            self._items = {}
            self._inserted = 0
            self._last_change = 0

        def restock(self, item_id, name, price_cents, count):
            if item_id in self._items:
                self._items[item_id]["count"] += count
            else:
                self._items[item_id] = {"name": name, "price": price_cents, "count": count}

        def insert_money(self, amount_cents):
            self._inserted += amount_cents

        def select(self, item_id):
            item = self._items.get(item_id)
            if item is None:
                return "unknown_item"
            if item["count"] <= 0:
                return "out_of_stock"
            if self._inserted < item["price"]:
                return "insufficient_funds"
            self._inserted -= item["price"]
            self._last_change = self._inserted
            self._inserted = 0
            item["count"] -= 1
            return "ok"

        def refund(self):
            amt = self._inserted
            self._inserted = 0
            return amt

        def inventory(self, item_id):
            return self._items[item_id]["count"] if item_id in self._items else None

        def change_due(self):
            return self._last_change

    ops = input["ops"]
    args = input["args"]
    instance = None
    results = []
    for op, a in zip(ops, args):
        if op == "VendingMachine":
            instance = VendingMachine()
            results.append(None)
        else:
            method = getattr(instance, op)
            results.append(method(*a))
    return results


PAYLOAD["entry"] = {
    "kind": "class_ops",
    "class": "VendingMachine",
    "constructor": {"params": []},
    "methods": [
        {"name": "restock", "params": [
            {"name": "item_id", "type": "string"},
            {"name": "name", "type": "string"},
            {"name": "price_cents", "type": "int"},
            {"name": "count", "type": "int"},
        ], "returns": "any"},
        {"name": "insert_money", "params": [{"name": "amount_cents", "type": "int"}], "returns": "any"},
        {"name": "select", "params": [{"name": "item_id", "type": "string"}], "returns": "string"},
        {"name": "refund", "params": [], "returns": "int"},
        {"name": "inventory", "params": [{"name": "item_id", "type": "string"}], "returns": "any"},
        {"name": "change_due", "params": [], "returns": "int"},
    ],
}


register(PAYLOAD, REFERENCE)
