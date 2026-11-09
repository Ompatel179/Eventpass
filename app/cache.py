import logging

import redis

logger = logging.getLogger("eventpass")

CACHE_TTL_SECONDS = 60
EVENTS_VERSION_KEY = "cache:events:version"


def event_key(event_id: int) -> str:
    return f"cache:event:{event_id}"



def events_list_key(redis_conn: redis.Redis, limit: int, offset: int) -> str | None:
    try:
        version = redis_conn.get(EVENTS_VERSION_KEY) or "0"
    except redis.RedisError:
        logger.warning("Cache read skipped: Redis unavailable")
        return None
    return f"cache:events:list:v{version}:{limit}:{offset}"


def bump_events_version(redis_conn: redis.Redis) -> None:
    try:
        redis_conn.incr(EVENTS_VERSION_KEY)
    except redis.RedisError:
        logger.warning("Cache invalidation skipped: Redis unavailable")


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


