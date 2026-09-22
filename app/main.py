from fastapi import FastAPI

from app.schemas import ChatRequest, ConfirmRequest
from app.agent.session import get_session
from app.agent.loop import run_agent, resume_agent

app = FastAPI(title="Customer Service Agent")


@app.post("/chat")
def chat(req: ChatRequest):
    session = get_session(req.session_id, req.user_id)
    result = run_agent(session, req.message)
    return result.to_dict()


@app.post("/confirm")
def confirm(req: ConfirmRequest):
    session = get_session(req.session_id)
    result = resume_agent(session, req.confirmed)
    return result.to_dict()