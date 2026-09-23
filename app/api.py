
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.agent import agent
from app.memory import memory

app = FastAPI(title="电商客服 Agent API")


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    need_handoff: bool = False


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message 不能为空")

    # 1. 取出历史消息
    history = memory.get(req.session_id)

    # 2. 追加用户新消息
    messages = history + [{"role": "user", "content": req.message}]

    # 3. 调用 Agent（内部自动完成 ReAct 循环）
    try:
        result = agent.invoke({"messages": messages})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent 调用失败: {e}")

    # 4. 更新记忆
    memory.append(req.session_id, result["messages"])

    # 5. 提取最终回复
    final_reply = result["messages"][-1].content
    need_handoff = final_reply.strip().startswith("[转人工]")

    return ChatResponse(
        session_id=req.session_id,
        reply=final_reply,
        need_handoff=need_handoff,
    )


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """清空指定会话的历史记录"""
    memory.clear(session_id)
    return {"status": "ok", "session_id": session_id}


@app.get("/health")
async def health():
    return {"status": "healthy"}