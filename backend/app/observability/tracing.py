"""Langfuse tracing that degrades gracefully.

If Langfuse keys are not configured (or the SDK isn't installed / the API differs across
versions), `observe` becomes a no-op decorator so the app runs identically without
observability. When keys are present, spans are captured automatically.
"""

from functools import wraps

from app.config import settings

_langfuse_enabled = bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)

_observe = None
if _langfuse_enabled:
    try:  # langfuse v2 decorator API
        from langfuse.decorators import observe as _observe  # type: ignore
    except Exception:
        try:  # langfuse v3 top-level API
            from langfuse import observe as _observe  # type: ignore
        except Exception:
            _observe = None
            _langfuse_enabled = False


def observe(*d_args, **d_kwargs):
    """Decorator usable as @observe or @observe(name=...). No-ops without Langfuse."""

    def decorator(func):
        if _observe is not None:
            return _observe(*d_args, **d_kwargs)(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        import asyncio

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    # Support bare @observe usage (first positional arg is the function).
    if len(d_args) == 1 and callable(d_args[0]) and not d_kwargs:
        func, d_args = d_args[0], ()
        return decorator(func)
    return decorator


def is_enabled() -> bool:
    return _langfuse_enabled
