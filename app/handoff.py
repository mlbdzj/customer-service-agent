import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings

# ============ 触发条件 1：用户明确要求 ============
HANDOFF_KEYWORDS = ["转人工", "人工客服", "找客服", "真人", "投诉", "要举报"]

def check_explicit_request(text: str) -> bool:
    return any(kw in text for kw in HANDOFF_KEYWORDS)


# ============ 触发条件 2：负面情绪（简单关键词版） ============
NEGATIVE_KEYWORDS = ["太差", "垃圾", "骗人", "欺骗", "愤怒", "无语", "恶心", "退钱"]

def check_negative_emotion(text: str) -> bool:
    return any(kw in text for kw in NEGATIVE_KEYWORDS)


# ============ 触发条件 3：连续未解决（用独立小模型判定） ============
RESOLVE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """判断用户的问题是否被客服的回答解决了。只输出一个单词：
yes - 问题得到明确解答或用户表示满意
no  - 问题未解决、回答含糊、或用户继续追问同一问题
只输出 yes 或 no，不要其他内容。"""),
    ("human", "用户问题：{question}\n客服回答：{answer}")
])

_judge_llm = ChatOpenAI(
    model=settings.LLM_MODEL,
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
    temperature=0,
)

def judge_resolved(question: str, answer: str) -> bool:
    """用独立小模型判断问题是否解决"""
    try:
        chain = RESOLVE_PROMPT | _judge_llm
        result = chain.invoke({"question": question, "answer": answer}).content.strip().lower()
        return result.startswith("yes")
    except Exception:
        # 判定失败时保守处理，视为已解决，避免误转
        return True


# ============ 综合判定 ============
def should_handoff(
    user_message: str,
    agent_reply: str,
    unresolved_count: int,
    max_unresolved: int = 2,
) -> tuple[bool, str]:
    """
    综合判定是否需要转人工。
    返回：(是否转人工, 转人工原因)
    """
    # 优先级 1：用户明确要求
    if check_explicit_request(user_message):
        return True, "用户明确要求转人工"

    # 优先级 2：强烈负面情绪
    if check_negative_emotion(user_message):
        return True, "检测到强烈负面情绪"

    # 优先级 3：连续未解决
    if unresolved_count >= max_unresolved:
        return True, f"连续{unresolved_count}轮未解决"

    return False, ""