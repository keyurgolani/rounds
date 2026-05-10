import time
from cart import total

def test_correctness_holds():
    cart = [{"qty": 1, "unit_price": p} for p in range(1, 1001)]
    assert total(cart) == 500500.00

def test_perf():
    cart = [{"qty": 1, "unit_price": 1.0} for _ in range(20000)]
    discounts = {f"D{i}": 0.01 for i in range(200)}
    start = time.monotonic()
    total(cart, discounts)
    assert time.monotonic() - start < 0.5, "total() should run linearly"
