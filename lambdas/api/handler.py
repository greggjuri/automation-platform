"""Lambda handler for Workflow CRUD API.

This module provides the main Lambda handler for API Gateway HTTP API,
implementing workflow CRUD operations using AWS Powertools for routing,
logging, and tracing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, NotFoundError
from pydantic import ValidationError

from models import (
    WorkflowCreate,
    WorkflowUpdate,
    generate_workflow_id,
    get_current_timestamp,
)
from repository import (
    create_workflow,
    delete_workflow,
    get_workflow,
    list_workflows,
    update_workflow,
)

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="automation-api")
tracer = Tracer(service="automation-api")
app = APIGatewayHttpResolver()


# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------


@app.get("/health")
@tracer.capture_method
def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Simple status object
    """
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# Workflow Routes
# -----------------------------------------------------------------------------


@app.get("/workflows")
@tracer.capture_method
def list_workflows_handler() -> dict:
    """List all workflows.

    Returns:
        Object with workflows array and count
    """
    logger.info("Listing workflows")

    workflows = list_workflows()

    return {"workflows": workflows, "count": len(workflows)}


@app.get("/workflows/<workflow_id>")
@tracer.capture_method
def get_workflow_handler(workflow_id: str) -> dict:
    """Get a single workflow by ID.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Workflow object

    Raises:
        NotFoundError: If workflow doesn't exist
    """
    logger.info("Getting workflow", workflow_id=workflow_id)

    workflow = get_workflow(workflow_id)

    if not workflow:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    return workflow


@app.post("/workflows")
@tracer.capture_method
def create_workflow_handler() -> dict:
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
        logger.warning("Validation failed", errors=str(e.errors()))
        raise BadRequestError(f"Invalid request: {e.errors()}")

    # Generate ID and timestamps
    workflow_id = generate_workflow_id()
    timestamp = get_current_timestamp()

    # Build item for DynamoDB
    item = {
        "workflow_id": workflow_id,
        "name": workflow_data.name,
        "description": workflow_data.description,
        "enabled": workflow_data.enabled,
        "trigger": workflow_data.trigger,
        "steps": workflow_data.steps,
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    # Save to DynamoDB
    created = create_workflow(item)
    logger.info("Workflow created", workflow_id=workflow_id)

    return created


@app.put("/workflows/<workflow_id>")
@tracer.capture_method
def update_workflow_handler(workflow_id: str) -> dict:
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

    # Parse and validate request body
    try:
        body = app.current_event.json_body or {}
        update_data = WorkflowUpdate(**body)
    except ValidationError as e:
        logger.warning("Validation failed", errors=str(e.errors()))
        raise BadRequestError(f"Invalid request: {e.errors()}")

    # Build updates dict with only provided fields
    updates = {
        "name": update_data.name,
        "description": update_data.description,
        "enabled": update_data.enabled,
        "trigger": update_data.trigger,
        "steps": update_data.steps,
        "updated_at": get_current_timestamp(),
    }

    # Filter out None values (except for updated_at which is always set)
    updates = {k: v for k, v in updates.items() if v is not None or k == "updated_at"}

    # Update in DynamoDB
    updated = update_workflow(workflow_id, updates)

    if not updated:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    logger.info("Workflow updated", workflow_id=workflow_id)

    return updated


@app.delete("/workflows/<workflow_id>")
@tracer.capture_method
def delete_workflow_handler(workflow_id: str) -> dict:
    """Delete a workflow.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Confirmation message

    Raises:
        NotFoundError: If workflow doesn't exist
    """
    logger.info("Deleting workflow", workflow_id=workflow_id)

    deleted = delete_workflow(workflow_id)

    if not deleted:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    logger.info("Workflow deleted", workflow_id=workflow_id)

    return {"message": f"Workflow {workflow_id} deleted", "workflow_id": workflow_id}


# -----------------------------------------------------------------------------
# Lambda Entry Point
# -----------------------------------------------------------------------------


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda entry point.

    This handler is invoked by API Gateway HTTP API.
    All routing is handled by the APIGatewayHttpResolver.

    Args:
        event: API Gateway HTTP API event
        context: Lambda context

    Returns:
        API Gateway HTTP API response
    """
    return app.resolve(event, context)
