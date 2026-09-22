import json
from langchain_core.tools import tool

FAKE_ORDERS = {
    "A12345": {"user_id": "u001", "status": "paid", "amount": 199, "refundable": True},
    "B67890": {"user_id": "u001", "status": "shipped", "amount": 99, "refundable": False},
    "C11111": {"user_id": "u002", "status": "paid", "amount": 59, "refundable": True},
}

def _get_order_raw(order_id: str) -> dict | None:
    return FAKE_ORDERS.get(order_id)

@tool
def get_order(order_id: str) -> str:
    """根据订单号查询订单状态、金额、是否可退。
    仅用于查询订单信息，不修改任何数据。
    参数 order_id 格式如 A12345，通常由用户提供。
    """
    order = _get_order_raw(order_id)
    if not order:
        return f"未找到订单 {order_id}"
    return json.dumps(order, ensure_ascii=False)

@tool
def cancel_order(order_id: str) -> str:
    """取消订单并退款。这是不可逆操作，必须在用户明确确认后调用。
    仅当用户明确表示要取消订单时使用，不可用于查询。
    参数 order_id 格式如 A12345。
    """
    order = _get_order_raw(order_id)
    if not order:
        return f"未找到订单 {order_id}"
    if not order["refundable"]:
        return f"订单 {order_id} 已发货，不可退"
    order["status"] = "cancelled"
    return f"订单 {order_id} 已取消，退款 {order['amount']} 元"