from pydantic import BaseModel, Field
from typing import Literal
from langchain.tools import tool


# ============ 模拟业务数据 ============
ORDERS = {
    "ORD-001": {"status": "已发货", "logistics": "顺丰 SF1234567890，预计明天送达",
                "amount": 299, "product": "云步通勤鞋", "user": "张三"},
    "ORD-002": {"status": "待发货", "logistics": "仓库备货中，预计24小时内出库",
                "amount": 159, "product": "轻风跑鞋", "user": "张三"},
    "ORD-003": {"status": "已签收", "logistics": "已签收，签收时间 2026-09-20",
                "amount": 499, "product": "户外冲锋衣", "user": "李四"},
}

STOCK = {
    "云步通勤鞋": {"42": 15, "43": 0, "44": 8},
    "轻风跑鞋":   {"40": 3, "41": 12, "42": 6},
    "户外冲锋衣": {"M": 5, "L": 10, "XL": 2},
}

PRODUCTS = {
    "云步通勤鞋": "轻量缓震通勤鞋，售价299元，适合日常通勤，尺码偏小建议选大半码",
    "轻风跑鞋":   "透气网面跑鞋，售价159元，适合5-10公里慢跑",
    "户外冲锋衣": "三层压胶防水冲锋衣，售价499元，适合户外徒步",
}


# ============ 工具 1：查询订单 ============
class OrderQueryInput(BaseModel):
    order_id: str = Field(
        description="订单号，格式为 'ORD-' 加三位数字，例如 ORD-001、ORD-002。"
                    "用户若未提供订单号，不要调用此工具，应先向用户询问。"
    )
    query_type: Literal["status", "logistics", "detail"] = Field(
        default="status",
        description="查询类型。"
                    "status=仅查订单状态（已发货/待发货/已签收）；"
                    "logistics=仅查物流轨迹和快递单号；"
                    "detail=查订单完整信息（状态+商品+金额+物流）。"
                    "用户问'到哪了/什么时候到'用 logistics；"
                    "用户问'我的订单状态/怎么样了'用 status；"
                    "用户问'订单详情/买了什么/多少钱'用 detail。"
    )

@tool(args_schema=OrderQueryInput)
def query_order(order_id: str, query_type: str = "status") -> str:
    """根据订单号查询订单的状态、物流或完整详情。

    使用场景：
    - 用户提供了订单号，想了解订单当前状态、物流进度或订单详情时调用。

    不要使用的场景：
    - 用户没有提供订单号时，不要调用，应先询问订单号。
    - 用户想退货/退款时，不要用此工具判断资格，应改用 check_refund_eligibility。
    - 用户想了解售后政策，应改用 query_after_sales_policy。

    返回：订单号对应的状态、物流或完整信息；若订单号不存在，返回"未找到订单"提示。
    """
    order = ORDERS.get(order_id.upper())
    if not order:
        return f"未找到订单 {order_id}，请确认订单号是否正确。"

    if query_type == "logistics":
        return f"订单 {order_id} 物流信息：{order['logistics']}"
    if query_type == "detail":
        return (f"订单 {order_id}：状态[{order['status']}]，商品[{order['product']}]，"
                f"金额[{order['amount']}元]，物流[{order['logistics']}]")
    return f"订单 {order_id} 当前状态：{order['status']}"


# ============ 工具 2：查询库存 ============
class InventoryInput(BaseModel):
    product_name: str = Field(
        description="商品名称，必须是商品库中的完整名称，例如 '云步通勤鞋'、'轻风跑鞋'。"
                    "若用户使用简称或描述（如'通勤鞋'），应先调用 search_products 确认商品全称。"
    )

@tool(args_schema=InventoryInput)
def check_inventory(product_name: str) -> str:
    """查询指定商品各尺码的库存数量。

    使用场景：
    - 用户询问某商品某个尺码是否有货、还剩多少件时调用。

    不要使用的场景：
    - 用户询问商品价格、材质、功能介绍时，应改用 search_products。
    - 商品名称不确定时，先调用 search_products 确认。

    返回：各尺码对应库存数量；若商品不存在，返回"未找到商品"。
    """
    stock = STOCK.get(product_name)
    if not stock:
        return f"未找到商品「{product_name}」的库存信息。"
    detail = "，".join(f"{size}码:{qty}件" for size, qty in stock.items())
    return f"「{product_name}」库存：{detail}"


# ============ 工具 3：搜索商品 ============
@tool
def search_products(keyword: str) -> str:
    """根据关键词搜索商品，返回匹配商品的名称和简介。

    使用场景：
    - 用户想找某类商品但不知道具体名称时调用，例如"你们有什么跑鞋"。
    - 用户使用商品简称或模糊描述时，先用此工具确认商品全称，再查库存或详情。

    不要使用的场景：
    - 已知商品全称时，直接调用 check_inventory 或查询详情，无需搜索。

    参数 keyword：搜索关键词，可以是商品名称的一部分或功能描述，如"跑鞋""通勤"。

    返回：匹配的商品名称和简介列表；无匹配时返回"没有找到"。
    """
    hits = [f"「{name}」：{desc}" for name, desc in PRODUCTS.items()
            if keyword in name or keyword in desc]
    if not hits:
        return f"没有找到与「{keyword}」相关的商品。"
    return "找到以下商品：\n" + "\n".join(hits)


# ============ 工具 4：退款资格判断 ============
class RefundEligibilityInput(BaseModel):
    order_id: str = Field(
        description="订单号，格式如 ORD-001。用户未提供订单号时不要调用，应先询问。"
    )

@tool(args_schema=RefundEligibilityInput)
def check_refund_eligibility(order_id: str) -> str:
    """判断指定订单是否满足7天无理由退货条件。

    使用场景：
    - 用户明确表示想退货、退单、退款，或询问"这个订单能退吗"时调用。

    不要使用的场景：
    - 用户只是查询订单状态或物流，应改用 query_order。
    - 用户询问退货政策条款本身，应改用 query_after_sales_policy。
    - 没有订单号时，先询问订单号。

    返回：是否满足退货条件的判断及原因；订单不存在时返回"未找到订单"。
    """
    order = ORDERS.get(order_id.upper())
    if not order:
        return f"未找到订单 {order_id}。"
    if order["status"] == "已签收":
        return f"订单 {order_id} 已签收，在7天无理由退货期内，可申请退货。"
    if order["status"] == "已发货":
        return f"订单 {order_id} 尚未签收，建议签收后7天内申请退货；也可联系客服拒收。"
    return f"订单 {order_id} 状态为[{order['status']}]，暂不支持退货申请。"


# ============ 工具 5：售后政策查询 ============
class PolicyInput(BaseModel):
    policy_type: Literal["退货", "换货", "退款", "运费"] = Field(
        description="政策类型，只能从以下四个值中选择："
                    "退货=7天无理由退货规则；"
                    "换货=换货时限和条件；"
                    "退款=退款到账时间和扣费规则；"
                    "运费=退换货运费由谁承担。"
    )

@tool(args_schema=PolicyInput)
def query_after_sales_policy(policy_type: str) -> str:
    """查询店铺的售后政策条款，包括退货、换货、退款、运费四类。

    使用场景：
    - 用户询问售后规则本身，例如"退货要多久内""退款什么时候到账""运费谁出"。

    不要使用的场景：
    - 用户针对具体订单询问能否退货，应改用 check_refund_eligibility。
    - 用户查询订单状态或物流，应改用 query_order。

    返回：对应类型的政策条款文本。
    """
    policies = {
        "退货": "签收后7天内可无理由退货，商品需保持完好、吊牌齐全。",
        "换货": "签收后15天内可换货，尺码不合适可免费换一次。",
        "退款": "退货签收后1-3个工作日内原路退款；质量问题全额退，非质量问题扣运费。",
        "运费": "质量问题运费商家承担；7天无理由退货运费买家承担。",
    }
    return policies.get(policy_type, f"未找到「{policy_type}」相关政策。")


TOOLS = [
    query_order,
    check_inventory,
    search_products,
    check_refund_eligibility,
    query_after_sales_policy,
]