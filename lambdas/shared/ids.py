"""ID generation utilities for execution engine.

Uses ULID for time-sortable, unique identifiers.
"""

from __future__ import annotations

import uuid
from datetime import datetime


def generate_execution_id() -> str:
    """Generate a time-sortable execution ID.

    Format: ex_{timestamp_hex}_{random_hex}

    This provides:
    - Time-based sorting (newer IDs sort after older ones)
    - Uniqueness across concurrent executions
    - Readable prefix for debugging

    Returns:
        Execution ID like "ex_018c8f3a1b2c_a1b2c3d4e5f6"
    """
    # Get current timestamp in milliseconds
    timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
    timestamp_hex = format(timestamp_ms, "012x")

    # Random component for uniqueness
    random_hex = uuid.uuid4().hex[:12]

    return f"ex_{timestamp_hex}_{random_hex}"


def get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO format.

    Returns:
        ISO 8601 formatted timestamp like "2025-01-15T10:30:00Z"
    """
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def calculate_ttl_timestamp(days: int = 90) -> int:
    """Calculate TTL timestamp for DynamoDB.

    Args:
        days: Number of days until expiration (default 90)

    Returns:
        Unix timestamp for TTL attribute
    """
    from datetime import timedelta

    expiry = datetime.utcnow() + timedelta(days=days)
    return int(expiry.timestamp())
