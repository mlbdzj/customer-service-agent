from app.agent.tools import _get_order, _cancel_order

def test_get_order_exists():
    assert "A12345" in _get_order("A12345")

def test_get_order_not_found():
    assert "未找到" in _get_order("ZZZ")

def test_cancel_not_refundable():
    assert "不可退" in _cancel_order("B67890")