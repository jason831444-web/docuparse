from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any


def sanitize_for_postgres(value: Any) -> Any:
    """Remove values PostgreSQL text/json fields cannot store."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [sanitize_for_postgres(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_for_postgres(item) for item in value)
    if isinstance(value, dict):
        return {
            str(sanitize_for_postgres(key)): sanitize_for_postgres(item)
            for key, item in value.items()
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Decimal):
        return value
    return value

