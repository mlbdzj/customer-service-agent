from collections import defaultdict
from dataclasses import dataclass, field
from app.config import settings


@dataclass
class SessionState:
    """单个会话的完整状态"""
    messages: list = field(default_factory=list)
    unresolved_count: int = 0          # 连续未解决轮次
    handoff_requested: bool = False    # 是否已触发转人工
    handoff_reason: str = ""           # 转人工原因，便于追踪


class SessionStore:
    """按 session_id 隔离的会话存储"""

    def __init__(self, max_turns: int = None):
        self.max_turns = max_turns or settings.MAX_HISTORY_TURNS
        self._store: dict[str, SessionState] = defaultdict(SessionState)

    def get(self, session_id: str) -> SessionState:
        return self._store[session_id]

    def append_messages(self, session_id: str, messages: list):
        state = self._store[session_id]
        state.messages.extend(messages)
        limit = self.max_turns * 4
        if len(state.messages) > limit:
            state.messages = state.messages[-limit:]

    def mark_unresolved(self, session_id: str):
        """标记一轮未解决"""
        self._store[session_id].unresolved_count += 1

    def mark_resolved(self, session_id: str):
        """标记问题已解决，重置计数"""
        self._store[session_id].unresolved_count = 0

    def set_handoff(self, session_id: str, reason: str):
        state = self._store[session_id]
        state.handoff_requested = True
        state.handoff_reason = reason

    def clear(self, session_id: str):
        self._store.pop(session_id, None)


store = SessionStore()