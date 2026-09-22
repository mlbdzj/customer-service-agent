"""
开发环境用内存字典模拟幂等。
生产环境替换为 Redis 实现，接口保持不变。
"""
import time

_locks: dict[str, float] = {}
_done: set[str] = set()

def acquire_lock(key: str, ttl: int = 30) -> bool:
    now = time.time()
    # 清理过期锁
    expired = [k for k, v in _locks.items() if v < now]
    for k in expired:
        _locks.pop(k, None)

    if key in _locks and _locks[key] > now:
        return False
    _locks[key] = now + ttl
    return True

def release_lock(key: str):
    _locks.pop(key, None)

def mark_done(key: str):
    _done.add(key)

def is_done(key: str) -> bool:
    return key in _done