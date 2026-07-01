import time
from collections import defaultdict


class AntiSpam:
    def __init__(self, delay_seconds: float = 0.7) -> None:
        self.delay_seconds = delay_seconds
        self._last_seen: dict[int, float] = defaultdict(float)

    def allowed(self, user_id: int) -> bool:
        now = time.monotonic()
        if now - self._last_seen[user_id] < self.delay_seconds:
            return False
        self._last_seen[user_id] = now
        return True
