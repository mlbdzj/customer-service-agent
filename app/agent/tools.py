import json

# ---------- 模拟订单库 ----------
FAKE_ORDERS = {
    "A12345": {"user_id": "u001", "status": "paid", "amount": 199, "refundable": True},
    "B67890": {"user_id": "u001", "status": "shipped", "amount": 99, "refundable": False},
    "C11111": {"user_id": "u002", "status": "paid", "amount": 59, "refundable": True},
}

def _get_order_raw(order_id: str) -> dict | None:
    return FAKE_ORDERS.get(order_id)

# ---------- 工具 schema（给 LLM 看） ----------
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": (
                "根据订单号查询订单状态、金额、是否可退。"
                "仅用于查询订单信息，不修改任何数据。"
                "参数 order_id 格式如 A12345，通常由用户提供。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "订单号，格式如 A12345",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
        {
            "type": "function",
            "function": {
                "name": "cancel_order",
                "description": (
                    "取消订单并退款。这是不可逆操作，必须在用户明确确认后调用。"
                    "仅当用户明确表示要取消订单时使用，不可用于查询。"
                    "参数 order_id 格式如 A12345。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "订单号，格式如 A12345",
                        }
                    },
                    "required": ["order_id"],
                },
            },
        },
]

# ---------- 工具实现 ----------
def _get_order(order_id: str) -> str:
    order = _get_order_raw(order_id)
    if not order:
        return f"未找到订单 {order_id}"
    return json.dumps(order, ensure_ascii=False)

def _cancel_order(order_id: str) -> str:
    order = _get_order_raw(order_id)
    if not order:
        return f"未找到订单 {order_id}"
    if not order["refundable"]:
        return f"订单 {order_id} 已发货，不可退"
    order["status"] = "cancelled"
    return f"订单 {order_id} 已取消，退款 {order['amount']} 元"

# ---------- 函数映射 ----------
TOOL_MAP = {
    "get_order": _get_order,
    "cancel_order": _cancel_order,
}

# 需要人工确认的工具
CONFIRM_REQUIRED = {"cancel_order"}