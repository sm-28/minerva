"""
shared/config/config_cache.py — In-memory configuration cache (Singleton).

Purpose:
    Provides fast, in-memory access to client configuration and system
    settings without hitting the database on every request.

Pattern:
    Singleton — one instance per process, shared across all sessions
    and requests.

Methods:
    ConfigCache.get_instance() → ConfigCache          (singleton accessor)
    config.get_business_config(business_id) → dict
    config.get_system_setting(key) → value
    config.invalidate(business_id)                    (force refresh for one business)
    config.refresh_all()                              (reload everything from DB)

Refresh Strategy:
    - Loaded from the database at service startup.
    - A background thread re-reads the database every 5 minutes.
    - For immediate refresh: Core exposes POST /internal/cache/refresh
      (internal network only).

No Redis:
    All caching is in-process. Each ECS task maintains its own copy.
    This is acceptable because config changes are infrequent admin
    operations and a 5-minute propagation delay is tolerable.
"""
