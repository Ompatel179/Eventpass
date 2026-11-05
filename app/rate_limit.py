import logging

import redis
from fastapi import HTTPException, Request

from app.config import REDIS_URL

logger = logging.getLogger("eventpass")

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def get_redis() -> redis.Redis:
    return redis_client


def client_ip(request: Request) -> str:
    cloudflare_ip = request.headers.get("cf-connecting-ip")
    if cloudflare_ip:
        return cloudflare_ip
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(
    redis_conn: redis.Redis, key: str, limit: int, window_seconds: int
) -> None:
    try:
        pipe = redis_conn.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        pipe.ttl(key)
        count, _, seconds_left = pipe.execute()
    except redis.RedisError:
        logger.warning("Rate limit skipped: Redis unavailable")
        return

    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(max(seconds_left, 1))},
        )