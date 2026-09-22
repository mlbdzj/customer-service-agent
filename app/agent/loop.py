import json
from openai import OpenAI

from app.config import settings
from app.agent.session import Session, get_session, clear_pending
from app.agent.tools import TOOLS_SCHEMA, TOOL_MAP, CONFIRM_REQUIRED, _get_order_raw
from app.services.idempotent import acquire_lock, release_lock, mark_done, is_done

client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)

SYSTEM_PROMPT = """你是企业客服助手。
- 查询订单、退订时，调用对应工具。
- 退订是不可逆操作，必须先向用户确认，得到明确同意后才能调用 cancel_order。
- 不确定时先反问，不要编造。
- 回答简洁、准确、有依据。
"""


class AgentResult:
    def __init__(self, type_: str, content: str | None = None, payload: dict | None = None):
        self.type = type_          # "answer" | "confirm"
        self.content = content
        self.payload = payload

    def to_dict(self):
        if self.type == "confirm":
            return {"type": "confirm", "payload": self.payload}
        return {"type": "answer", "content": self.content}


def _to_message_dict(msg) -> dict:
    """把 OpenAI 返回的 message 对象转成可存储的 dict"""
    d = {"role": msg.role, "content": msg.content}
    if getattr(msg, "tool_calls", None):
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return d


def _call_llm(messages: list[dict]):
    resp = client.chat.completions.create(
        model=settings.model,
        messages=messages,
        tools=TOOLS_SCHEMA,
        temperature=0,
    )
    return resp.choices[0].message


def _execute_tool(tool_call: dict, session: Session) -> str:
    """执行单个工具调用，含权限、幂等、确认逻辑"""
    name = tool_call["function"]["name"]
    try:
        args = json.loads(tool_call["function"]["arguments"])
    except json.JSONDecodeError:
        return "参数解析失败"

    order_id = args.get("order_id", "")

    # 权限校验
    if name in ("get_order", "cancel_order"):
        order = _get_order_raw(order_id)
        if order and order.get("user_id") != session.user_id:
            return "无权访问该订单"

    # 幂等
    idem_key = None
    if name == "cancel_order":
        idem_key = f"{session.user_id}:{name}:{order_id}"
        if is_done(idem_key):
            return "该订单已退订，无需重复操作"
        if not acquire_lock(idem_key):
            return "操作正在处理中，请稍后"

    try:
        fn = TOOL_MAP.get(name)
        if not fn:
            return f"未知工具 {name}"
        output = fn(**args)
    except Exception as e:
        output = f"工具执行失败：{e}"
    finally:
        if idem_key:
            release_lock(idem_key)

    if name == "cancel_order" and idem_key and "已取消" in str(output):
        mark_done(idem_key)

    return str(output)


def run_agent(session: Session, user_message: str) -> AgentResult:
    """跑 ReAct 循环，遇到需要确认的工具就中断"""
    # 如果上一轮有待确认的，先处理（这里不会走到，confirm 接口单独处理）
    session.messages.append({"role": "user", "content": user_message})
    return _run_loop(session)


def resume_agent(session: Session, confirmed: bool) -> AgentResult:
    """用户确认后，继续执行"""
    pending = session.pending
    if not pending:
        return AgentResult("answer", "没有待确认的操作")

    tool_call = pending["tool_call"]
    tool_call_id = tool_call["id"]

    if confirmed:
        output = _execute_tool(tool_call, session)
    else:
        output = "用户取消了本次操作"

    # 把工具结果加进历史
    session.messages.append({
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": output,
    })

    clear_pending(session.session_id)
    return _run_loop(session)


def _run_loop(session: Session) -> AgentResult:
    """核心循环：LLM → 判断 → 执行工具 → 回灌 → 再 LLM"""
    for _ in range(settings.max_steps):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + session.messages
        msg = _call_llm(messages)
        msg_dict = _to_message_dict(msg)
        session.messages.append(msg_dict)

        # 无工具调用 → 结束
        if not msg_dict.get("tool_calls"):
            return AgentResult("answer", msg_dict.get("content") or "")

        # 有工具调用，检查是否需要确认
        for tc in msg_dict["tool_calls"]:
            name = tc["function"]["name"]
            if name in CONFIRM_REQUIRED:
                # 中断，存 pending，等用户确认
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                session.pending = {
                    "tool_call": tc,
                    "question": f"确认执行 {name}（订单 {args.get('order_id', '')}）吗？",
                }
                return AgentResult("confirm", payload={
                    "tool": name,
                    "args": args,
                    "question": session.pending["question"],
                })

        # 无需确认，直接执行所有工具
        for tc in msg_dict["tool_calls"]:
            output = _execute_tool(tc, session)
            session.messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": output,
            })

    return AgentResult("answer", "达到最大步数，任务未完成。")