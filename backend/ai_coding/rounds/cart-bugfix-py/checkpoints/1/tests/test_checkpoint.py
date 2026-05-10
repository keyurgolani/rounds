from cart import total, apply_discount_code

def test_welcome_code_takes_10pct():
    cart = [{"qty": 2, "unit_price": 10}]
    apply_discount_code(cart, "WELCOME10")
    assert total(cart) == 18.00

def test_unknown_code_is_noop_and_returns_false():
    cart = [{"qty": 2, "unit_price": 10}]
    assert apply_discount_code(cart, "BOGUS") is False
    assert total(cart) == 20.00

def test_blackfriday_code_takes_50pct():
    # This code only exists in discounts.json. A solution that hardcodes
    # WELCOME10 / VIP20 will fail this test.
    cart = [{"qty": 2, "unit_price": 10}]
    apply_discount_code(cart, "BLACKFRIDAY50")
    assert total(cart) == 10.00
