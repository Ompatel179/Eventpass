import logging

import redis

logger = logging.getLogger("eventpass")

CACHE_TTL_SECONDS = 60
EVENTS_LIST_KEY = "cache:events:list"


def event_key(event_id: int) -> str:
    return f"cache:event:{event_id}"


def cache_get(redis_conn: redis.Redis, key: str) -> str | None:
    try:
        return redis_conn.get(key)
    except redis.RedisError:
        logger.warning("Cache read skipped: Redis unavailable")
        return None


def cache_set(redis_conn: redis.Redis, key: str, value: str) -> None:
    try:
        redis_conn.set(key, value, ex=CACHE_TTL_SECONDS)
    except redis.RedisError:
        logger.warning("Cache write skipped: Redis unavailable")


def cache_delete(redis_conn: redis.Redis, key: str) -> None:
    try:
        redis_conn.delete(key)
    except redis.RedisError:
        logger.warning("Cache delete skipped: Redis unavailable")