from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by client IP; swap for a user-id key function once auth is mandatory.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
