import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, status


class SlidingWindowRateLimiter:
    """
    Sliding window in-memory rate limiter per workspace and user.
    Protects expensive LLM and Document Comparison endpoints against abuse and cost overruns.
    """
    def __init__(self, limit: int = 30, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str):
        now = time.time()
        window_start = now - self.window_seconds
        # Clean older requests outside the window
        valid_requests = [t for t in self.requests[key] if t > window_start]
        self.requests[key] = valid_requests

        if len(valid_requests) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.limit} requests per {self.window_seconds}s allowed."
            )
        self.requests[key].append(now)


rag_rate_limiter = SlidingWindowRateLimiter(limit=30, window_seconds=60)
compare_rate_limiter = SlidingWindowRateLimiter(limit=30, window_seconds=60)
