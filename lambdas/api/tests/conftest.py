"""Pytest configuration and fixtures for API Lambda tests."""

from __future__ import annotations

import os
import sys

import pytest

# Add the lambda directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set required environment variables before importing modules
os.environ.setdefault("TABLE_NAME", "test-Workflows")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("POWERTOOLS_SERVICE_NAME", "automation-api")
os.environ.setdefault("POWERTOOLS_LOG_LEVEL", "DEBUG")


@pytest.fixture
def workflow_create_data() -> dict:
    """Sample data for creating a workflow."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "enabled": True,
        "trigger": {"type": "manual"},
        "steps": [{"type": "log", "message": "Hello"}],
    }


@pytest.fixture
def workflow_update_data() -> dict:
    """Sample data for updating a workflow."""
    return {
        "name": "Updated Workflow",
        "description": "Updated description",
    }


@pytest.fixture
def sample_workflow() -> dict:
    """A complete workflow as stored in DynamoDB."""
    return {
        "workflow_id": "wf_test123",
        "name": "Test Workflow",
        "description": "A test workflow",
        "enabled": True,
        "trigger": {"type": "manual"},
        "steps": [{"type": "log", "message": "Hello"}],
        "created_at": "2025-01-15T10:30:00Z",
        "updated_at": "2025-01-15T10:30:00Z",
    }
