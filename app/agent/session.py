from dataclasses import dataclass, field

@dataclass
class Session:
    session_id: str
    user_id: str
    messages: list[dict] = field(default_factory=list)
    # 待确认的工具调用信息，None 表示无待确认
    pending: dict | None = None

_sessions: dict[str, Session] = {}

def get_session(session_id: str, user_id: str | None = None) -> Session:
    if session_id not in _sessions:
        _sessions[session_id] = Session(session_id=session_id, user_id=user_id or "")
    return _sessions[session_id]

def clear_pending(session_id: str):
    s = _sessions.get(session_id)
    if s:
        s.pending = None
