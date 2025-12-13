"""Pydantic models for Workflow API.

This module defines request/response models and helper functions
for the workflow CRUD API.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Request Models
# -----------------------------------------------------------------------------


class WorkflowCreate(BaseModel):
    """Request model for creating a workflow."""

    name: str = Field(..., min_length=1, max_length=100, description="Workflow name")
    description: str = Field(default="", max_length=500, description="Workflow description")
    enabled: bool = Field(default=True, description="Whether workflow is active")
    trigger: dict[str, Any] = Field(default_factory=dict, description="Trigger configuration")
    steps: list[dict[str, Any]] = Field(default_factory=list, description="Workflow steps")


class WorkflowUpdate(BaseModel):
    """Request model for updating a workflow.

    All fields are optional - only provided fields will be updated.
    """

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    enabled: bool | None = None
    trigger: dict[str, Any] | None = None
    steps: list[dict[str, Any]] | None = None


# -----------------------------------------------------------------------------
# Response Models
# -----------------------------------------------------------------------------


class WorkflowResponse(BaseModel):
    """Response model for workflow data."""

    workflow_id: str
    name: str
    description: str
    enabled: bool
    trigger: dict[str, Any]
    steps: list[dict[str, Any]]
    created_at: str
    updated_at: str


class WorkflowListResponse(BaseModel):
    """Response model for listing workflows."""

    workflows: list[dict[str, Any]]
    count: int


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    message: str
    workflow_id: str


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = "ok"


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def generate_workflow_id() -> str:
    """Generate a unique workflow ID with 'wf_' prefix.

    Returns:
        A unique ID like 'wf_a1b2c3d4e5f6'
    """
    return f"wf_{uuid.uuid4().hex[:12]}"


def get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO 8601 format.

    Returns:
        Timestamp string like '2025-01-15T10:30:00Z'
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
