from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.agent import agent
from app.memory import store
from app.handoff import should_handoff, judge_resolved

app = FastAPI(title="电商客服 Agent API")


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    need_handoff: bool = False
    handoff_reason: str = ""


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message 不能为空")

    state = store.get(req.session_id)

    # 如果已经转人工，后续消息不再走 Agent
    if state.handoff_requested:
        return ChatResponse(
            session_id=req.session_id,
            reply="您正在与人工客服对话中，请稍候。",
            need_handoff=True,
            handoff_reason=state.handoff_reason,
        )

    # 1. 组装消息并调用 Agent
    messages = state.messages + [{"role": "user", "content": req.message}]
    try:
        result = agent.invoke({"messages": messages})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 调用失败: {e}")

    reply = result["messages"][-1].content

    # 2. 更新消息历史
    store.append_messages(req.session_id, result["messages"])

    # 3. 用独立模型判定本轮是否解决
    resolved = judge_resolved(req.message, reply)
    if resolved:
        store.mark_resolved(req.session_id)
    else:
        store.mark_unresolved(req.session_id)

    # 4. 综合判定是否转人工
    current_state = store.get(req.session_id)
    need_handoff, reason = should_handoff(
        user_message=req.message,
        agent_reply=reply,
        unresolved_count=current_state.unresolved_count,
    )

    if need_handoff:
        store.set_handoff(req.session_id, reason)
        # 真实项目：这里对接工单系统，推送完整对话上下文
        reply = f"{reply}\n\n[已为您转接人工客服，原因：{reason}]"

    return ChatResponse(
        session_id=req.session_id,
        reply=reply,
        need_handoff=need_handoff,
        handoff_reason=reason,
    )


@app.get("/session/{session_id}/debug")
async def debug_session(session_id: str):
    """调试接口：查看会话当前状态，方便排查转人工问题"""
    state = store.get(session_id)
    return {
        "unresolved_count": state.unresolved_count,
        "handoff_requested": state.handoff_requested,
        "handoff_reason": state.handoff_reason,
        "message_count": len(state.messages),
    }