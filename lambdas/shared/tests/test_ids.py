"""Tests for ids module."""

import time
from datetime import datetime, timedelta

from shared.ids import (
    calculate_ttl_timestamp,
    generate_execution_id,
    get_current_timestamp,
)


class TestGenerateExecutionId:
    """Test execution ID generation."""

    def test_has_prefix(self):
        """Test that execution ID has correct prefix."""
        execution_id = generate_execution_id()
        assert execution_id.startswith("ex_")

    def test_format(self):
        """Test execution ID format."""
        execution_id = generate_execution_id()
        parts = execution_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "ex"
        # Timestamp hex is 12 chars
        assert len(parts[1]) == 12
        # Random hex is 12 chars
        assert len(parts[2]) == 12

    def test_uniqueness(self):
        """Test that generated IDs are unique."""
        ids = {generate_execution_id() for _ in range(100)}
        assert len(ids) == 100

    def test_sortable(self):
        """Test that IDs are time-sortable."""
        id1 = generate_execution_id()
        time.sleep(0.01)  # Small delay to ensure different timestamp
        id2 = generate_execution_id()
        # Later ID should sort after earlier one
        assert id2 > id1

    def test_all_hex_chars(self):
        """Test that ID parts contain only valid hex characters."""
        execution_id = generate_execution_id()
        parts = execution_id.split("_")
        # Validate timestamp part is hex
        int(parts[1], 16)  # Will raise if not valid hex
        # Validate random part is hex
        int(parts[2], 16)  # Will raise if not valid hex


class TestGetCurrentTimestamp:
    """Test timestamp generation."""

    def test_iso_format(self):
        """Test that timestamp is in ISO format."""
        timestamp = get_current_timestamp()
        # Should not raise
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_ends_with_z(self):
        """Test that timestamp ends with Z (UTC)."""
        timestamp = get_current_timestamp()
        assert timestamp.endswith("Z")

    def test_reasonable_time(self):
        """Test that timestamp is a reasonable recent time."""
        timestamp = get_current_timestamp()
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        now = datetime.utcnow()
        # Should be within 1 second of now
        diff = abs((now - parsed.replace(tzinfo=None)).total_seconds())
        assert diff < 1


class TestCalculateTtlTimestamp:
    """Test TTL timestamp calculation."""

    def test_default_90_days(self):
        """Test default 90-day TTL."""
        ttl = calculate_ttl_timestamp()
        expected = datetime.utcnow() + timedelta(days=90)
        # Should be within a few seconds of expected
        diff = abs(ttl - expected.timestamp())
        assert diff < 5

    def test_custom_days(self):
        """Test custom day count."""
        ttl = calculate_ttl_timestamp(days=30)
        expected = datetime.utcnow() + timedelta(days=30)
        diff = abs(ttl - expected.timestamp())
        assert diff < 5

    def test_returns_integer(self):
        """Test that TTL is an integer."""
        ttl = calculate_ttl_timestamp()
        assert isinstance(ttl, int)

    def test_in_future(self):
        """Test that TTL is in the future."""
        ttl = calculate_ttl_timestamp(days=1)
        now = int(datetime.utcnow().timestamp())
        assert ttl > now
