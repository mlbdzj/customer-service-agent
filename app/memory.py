from collections import defaultdict
from app.config import settings


class ConversationMemory:
    """按 session_id 隔离的对话记忆，采用滑窗策略保留最近 N 轮。"""

    def __init__(self, max_turns: int = None):
        self.max_turns = max_turns or settings.MAX_HISTORY_TURNS
        self._store: dict[str, list] = defaultdict(list)

    def get(self, session_id: str) -> list:
        """获取该会话的历史消息"""
        return self._store[session_id]

    def append(self, session_id: str, messages: list):
        """追加消息并裁剪到滑窗大小"""
        self._store[session_id].extend(messages)
        # 每轮对话通常产生 user + assistant 两条，工具消息可能更多
        # 这里按消息条数上限裁剪，保留最近 max_turns*2 条
        limit = self.max_turns * 4
        if len(self._store[session_id]) > limit:
            self._store[session_id] = self._store[session_id][-limit:]

    def clear(self, session_id: str):
        """清空指定会话"""
        self._store.pop(session_id, None)


memory = ConversationMemory()