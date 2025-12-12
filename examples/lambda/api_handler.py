"""
Example: API Gateway Lambda Handler

This example demonstrates the standard pattern for Lambda functions handling
HTTP requests from API Gateway. Use this as a template for CRUD endpoints.

Key patterns:
- AWS Powertools for logging, tracing, and routing
- Pydantic for request/response validation
- Proper error handling with HTTP status codes
- DynamoDB integration with boto3 resource

Copy this file and adapt for your specific endpoint.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, NotFoundError
from boto3.dynamodb.conditions import Key
from pydantic import BaseModel, Field, ValidationError

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

TABLE_NAME = os.environ.get("TABLE_NAME", "Workflows")

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="api-handler")
tracer = Tracer(service="api-handler")
app = APIGatewayHttpResolver()

# -----------------------------------------------------------------------------
# AWS Resources
# -----------------------------------------------------------------------------

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

# -----------------------------------------------------------------------------
# Pydantic Models
# -----------------------------------------------------------------------------


class WorkflowCreate(BaseModel):
    """Request model for creating a workflow."""

    name: str = Field(..., min_length=1, max_length=100, description="Workflow name")
    description: str = Field(default="", max_length=500)
    enabled: bool = Field(default=True)


class WorkflowUpdate(BaseModel):
    """Request model for updating a workflow."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    enabled: bool | None = None


class WorkflowResponse(BaseModel):
    """Response model for workflow data."""

    workflow_id: str
    name: str
    description: str
    enabled: bool
    created_at: str
    updated_at: str


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def generate_id(prefix: str = "wf") -> str:
    """Generate a unique ID with prefix."""
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"


# -----------------------------------------------------------------------------
# Route Handlers
# -----------------------------------------------------------------------------


@app.get("/workflows")
@tracer.capture_method
def list_workflows() -> dict:
    """List all workflows.

    Returns paginated list of workflows ordered by creation date.
    """
    logger.info("Listing workflows")

    # Scan table (acceptable for small datasets)
    # For large datasets, use query with GSI
    response = table.scan(
        ProjectionExpression="workflow_id, #n, description, enabled, created_at",
        ExpressionAttributeNames={"#n": "name"},  # 'name' is reserved word
    )

    workflows = response.get("Items", [])
    logger.info("Found workflows", count=len(workflows))

    return {"workflows": workflows, "count": len(workflows)}


@app.get("/workflows/<workflow_id>")
@tracer.capture_method
def get_workflow(workflow_id: str) -> dict:
    """Get a single workflow by ID.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Workflow details

    Raises:
        NotFoundError: If workflow doesn't exist
    """
    logger.info("Getting workflow", workflow_id=workflow_id)

    response = table.get_item(Key={"workflow_id": workflow_id})
    item = response.get("Item")

    if not item:
        logger.warning("Workflow not found", workflow_id=workflow_id)
        raise NotFoundError(f"Workflow {workflow_id} not found")

    return item


@app.post("/workflows")
@tracer.capture_method
def create_workflow() -> dict:
    """Create a new workflow.

    Returns:
        Created workflow with generated ID

    Raises:
        BadRequestError: If request body is invalid
    """
    logger.info("Creating workflow")

    # Parse and validate request body
    try:
        body = app.current_event.json_body or {}
        workflow_data = WorkflowCreate(**body)
    except ValidationError as e:
        logger.warning("Validation failed", errors=e.errors())
        raise BadRequestError(f"Invalid request: {e.errors()}")

    # Generate ID and timestamps
    workflow_id = generate_id("wf")
    timestamp = get_current_timestamp()

    # Build item for DynamoDB
    item = {
        "workflow_id": workflow_id,
        "name": workflow_data.name,
        "description": workflow_data.description,
        "enabled": workflow_data.enabled,
        "trigger": {},  # Placeholder for trigger config
        "steps": [],  # Placeholder for workflow steps
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    # Save to DynamoDB
    table.put_item(Item=item)
    logger.info("Workflow created", workflow_id=workflow_id)

    return item


@app.put("/workflows/<workflow_id>")
@tracer.capture_method
def update_workflow(workflow_id: str) -> dict:
    """Update an existing workflow.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Updated workflow

    Raises:
        NotFoundError: If workflow doesn't exist
        BadRequestError: If request body is invalid
    """
    logger.info("Updating workflow", workflow_id=workflow_id)

    # Verify workflow exists
    existing = table.get_item(Key={"workflow_id": workflow_id}).get("Item")
    if not existing:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    # Parse and validate request body
    try:
        body = app.current_event.json_body or {}
        update_data = WorkflowUpdate(**body)
    except ValidationError as e:
        logger.warning("Validation failed", errors=e.errors())
        raise BadRequestError(f"Invalid request: {e.errors()}")

    # Build update expression for provided fields only
    update_parts = []
    expression_values = {}
    expression_names = {}

    if update_data.name is not None:
        update_parts.append("#n = :name")
        expression_values[":name"] = update_data.name
        expression_names["#n"] = "name"

    if update_data.description is not None:
        update_parts.append("description = :description")
        expression_values[":description"] = update_data.description

    if update_data.enabled is not None:
        update_parts.append("enabled = :enabled")
        expression_values[":enabled"] = update_data.enabled

    # Always update timestamp
    update_parts.append("updated_at = :updated_at")
    expression_values[":updated_at"] = get_current_timestamp()

    # Execute update
    response = table.update_item(
        Key={"workflow_id": workflow_id},
        UpdateExpression="SET " + ", ".join(update_parts),
        ExpressionAttributeValues=expression_values,
        ExpressionAttributeNames=expression_names if expression_names else None,
        ReturnValues="ALL_NEW",
    )

    updated_item = response.get("Attributes", {})
    logger.info("Workflow updated", workflow_id=workflow_id)

    return updated_item


@app.delete("/workflows/<workflow_id>")
@tracer.capture_method
def delete_workflow(workflow_id: str) -> dict:
    """Delete a workflow.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Confirmation message

    Raises:
        NotFoundError: If workflow doesn't exist
    """
    logger.info("Deleting workflow", workflow_id=workflow_id)

    # Verify workflow exists before deleting
    existing = table.get_item(Key={"workflow_id": workflow_id}).get("Item")
    if not existing:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    # Delete from DynamoDB
    table.delete_item(Key={"workflow_id": workflow_id})
    logger.info("Workflow deleted", workflow_id=workflow_id)

    return {"message": f"Workflow {workflow_id} deleted", "workflow_id": workflow_id}


# -----------------------------------------------------------------------------
# Lambda Handler
# -----------------------------------------------------------------------------


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda entry point.

    This handler is invoked by API Gateway HTTP API.
    All routing is handled by the APIGatewayHttpResolver.
    """
    return app.resolve(event, context)
