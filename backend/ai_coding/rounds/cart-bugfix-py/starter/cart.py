from typing import List, Dict

def total(cart: List[Dict], discounts: Dict[str, float] | None = None) -> float:
    discounts = discounts or {}
    subtotal = 0.0
    for item in cart:
        # The math here doesn't agree with what the tests assert.
        # Find what's wrong and fix it.
        subtotal += item["qty"] // 1 * item["unit_price"]
    return round(subtotal, 2)

def apply_discount_code(cart, code):
    # Implemented in the discount-codes checkpoint.
    raise NotImplementedError
