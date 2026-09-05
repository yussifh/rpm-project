"""
Redis connection singleton.

Used for:
  - Caching the latest vitals reading per patient (fast dashboard reads)
  - JWT refresh-token / blacklist storage
  - Rate limiting (future)
"""

import redis

from app.core.config import settings

try:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()
except (redis.ConnectionError, redis.AuthenticationError):
    import fakeredis
    redis_client = fakeredis.FakeRedis(decode_responses=True)


def get_redis() -> redis.Redis:
    """FastAPI dependency to inject the Redis client into services."""
    return redis_client
