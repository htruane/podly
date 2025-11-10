import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])

_cache_store: Dict[str, Dict[str, Any]] = {}


def ttl_cache(ttl_seconds: int = 300) -> Callable[[F], F]:
    """
    Simple TTL-based cache decorator for methods.

    Args:
        ttl_seconds: Time-to-live in seconds (default 300 = 5 minutes)

    Usage:
        @ttl_cache(ttl_seconds=600)
        def my_method(self, post_id: int) -> Dict:
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = _make_cache_key(func.__name__, args, kwargs)

            if cache_key in _cache_store:
                cached_data = _cache_store[cache_key]
                if time.time() - cached_data["timestamp"] < ttl_seconds:
                    return cached_data["value"]

            result = func(*args, **kwargs)
            _cache_store[cache_key] = {"value": result, "timestamp": time.time()}

            return result

        return cast(F, wrapper)

    return decorator


def invalidate_cache(func_name: str, *args: Any, **kwargs: Any) -> None:
    """
    Invalidate a specific cache entry.

    Args:
        func_name: Name of the cached function
        *args, **kwargs: Arguments used to generate the cache key
    """
    cache_key = _make_cache_key(func_name, args, kwargs)
    _cache_store.pop(cache_key, None)


def clear_all_cache() -> None:
    """Clear all cached data."""
    _cache_store.clear()


def _make_cache_key(func_name: str, args: tuple, kwargs: Dict) -> str:
    """
    Generate a cache key from function name and arguments.

    Args:
        func_name: Name of the function
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    key_parts = [func_name]

    for arg in args[1:]:
        if hasattr(arg, "id"):
            key_parts.append(f"{type(arg).__name__}:{arg.id}")
        elif isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))

    for k, v in sorted(kwargs.items()):
        if hasattr(v, "id"):
            key_parts.append(f"{k}={type(v).__name__}:{v.id}")
        elif isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}={v}")

    return ":".join(key_parts)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache size and entry count
    """
    return {
        "entry_count": len(_cache_store),
        "cache_keys": list(_cache_store.keys()),
    }
