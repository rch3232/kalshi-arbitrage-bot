"""
Helper utilities for the Kalshi arbitrage bot.
"""

def safe_get(obj, key, default=None):
    """
    Safely get a value from either a dictionary or an object.

    The Kalshi SDK returns Market objects, but sometimes we may have dicts.
    This helper handles both cases.

    Args:
        obj: Dictionary or object to get value from
        key: Key/attribute name
        default: Default value if key/attribute doesn't exist

    Returns:
        The value, or default if not found
    """
    if isinstance(obj, dict):
        return obj.get(key, default)
    else:
        return getattr(obj, key, default)
