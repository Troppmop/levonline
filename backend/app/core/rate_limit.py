from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Backed by Redis so limits are enforced consistently across multiple
# backend instances/processes, not just per-process in memory. Tests run
# without a Redis instance available, so they fall back to in-memory
# storage — per-process limiting is fine there since tests run in one process.
_storage_uri = "memory://" if settings.ENVIRONMENT == "test" else settings.REDIS_URL

limiter = Limiter(key_func=get_remote_address, storage_uri=_storage_uri)
