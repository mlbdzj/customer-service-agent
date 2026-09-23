from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from app.config import settings
from app.tools import TOOLS


SYSTEM_PROMPT = """你是一个专业、友好的电商客服助手，服务于一家运动鞋服店铺。

你的职责：
1. 商品咨询：解答商品信息、价格、尺码建议
2. 库存查询：告诉用户具体尺码是否有货
3. 订单查询：查询订单状态和物流
4. 售后处理：解答退货/换货/退款政策，判断退款资格

工作原则：
- 必须先调用工具获取真实数据，绝不凭空编造订单状态、库存或政策
- 如果用户没提供订单号，先礼貌地询问
- 如果工具返回"未找到"，如实告知用户，不要猜测
- 回答简洁友好，控制在3句话以内
- 遇到投诉、要求转人工、或连续两轮无法解决的问题，回复以"[转人工]"开头并说明原因
"""


def build_agent():
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=settings.TEMPERATURE,
    )

    agent = create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent


# 单例，全局复用一个 Agent 实例
agent = build_agent()