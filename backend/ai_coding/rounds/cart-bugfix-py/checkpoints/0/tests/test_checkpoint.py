from cart import total

def test_simple_total():
    assert total([{"qty": 2.5, "unit_price": 10}]) == 25.0

def test_fractional_quantity():
    assert total([{"qty": 1.5, "unit_price": 10}]) == 15.0

def test_multi_item():
    # Two fractional quantities; both lines must use float math for the
    # total to come out right. Buggy floor-divide gives 10.0+15.0 = 25.0.
    assert total([{"qty": 1.5, "unit_price": 10.0}, {"qty": 3.5, "unit_price": 4.0}]) == 29.0
