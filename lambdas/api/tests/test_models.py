"""Tests for Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import (
    WorkflowCreate,
    WorkflowUpdate,
    generate_workflow_id,
    get_current_timestamp,
)


class TestWorkflowCreate:
    """Tests for WorkflowCreate model."""

    def test_valid_minimal(self):
        """Test creating workflow with only required fields."""
        data = WorkflowCreate(name="Test")

        assert data.name == "Test"
        assert data.description == ""
        assert data.enabled is True
        assert data.trigger == {}
        assert data.steps == []

    def test_valid_full(self, workflow_create_data):
        """Test creating workflow with all fields."""
        data = WorkflowCreate(**workflow_create_data)

        assert data.name == "Test Workflow"
        assert data.description == "A test workflow"
        assert data.enabled is True
        assert data.trigger == {"type": "manual"}
        assert len(data.steps) == 1

    def test_invalid_empty_name(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowCreate(name="")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)

    def test_invalid_name_too_long(self):
        """Test that name over 100 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowCreate(name="x" * 101)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)

    def test_invalid_description_too_long(self):
        """Test that description over 500 chars is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowCreate(name="Test", description="x" * 501)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("description",)

    def test_missing_name(self):
        """Test that missing name raises error."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowCreate()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)


class TestWorkflowUpdate:
    """Tests for WorkflowUpdate model."""

    def test_empty_update(self):
        """Test that empty update is valid (no fields required)."""
        data = WorkflowUpdate()

        assert data.name is None
        assert data.description is None
        assert data.enabled is None
        assert data.trigger is None
        assert data.steps is None

    def test_partial_update(self, workflow_update_data):
        """Test updating only some fields."""
        data = WorkflowUpdate(**workflow_update_data)

        assert data.name == "Updated Workflow"
        assert data.description == "Updated description"
        assert data.enabled is None

    def test_invalid_name_too_long(self):
        """Test that name over 100 chars is rejected in update."""
        with pytest.raises(ValidationError):
            WorkflowUpdate(name="x" * 101)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_generate_workflow_id_format(self):
        """Test that generated ID has correct format."""
        workflow_id = generate_workflow_id()

        assert workflow_id.startswith("wf_")
        assert len(workflow_id) == 15  # wf_ + 12 hex chars

    def test_generate_workflow_id_unique(self):
        """Test that generated IDs are unique."""
        ids = [generate_workflow_id() for _ in range(100)]

        assert len(set(ids)) == 100  # All unique

    def test_get_current_timestamp_format(self):
        """Test that timestamp has correct ISO format."""
        timestamp = get_current_timestamp()

        # Should match pattern: 2025-01-15T10:30:00Z
        assert len(timestamp) == 20
        assert timestamp.endswith("Z")
        assert "T" in timestamp
