"""Lambda handler for Workflow CRUD API and Execution endpoints.

This module provides the main Lambda handler for API Gateway HTTP API,
implementing workflow CRUD operations and execution management using
AWS Powertools for routing, logging, and tracing.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import boto3
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
from eventbridge import delete_schedule_rule, sync_workflow_rule
from repository import (
    create_workflow,
    delete_workflow,
    get_execution,
    get_workflow,
    list_executions,
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

# SQS client for execution queue
sqs_client = boto3.client("sqs")
EXECUTION_QUEUE_URL = os.environ.get("EXECUTION_QUEUE_URL", "")


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

    # Create EventBridge rule if cron trigger
    try:
        sync_workflow_rule(
            workflow_id=workflow_id,
            old_trigger=None,  # New workflow, no old trigger
            new_trigger=workflow_data.trigger,
        )
    except Exception as e:
        # Log but don't fail the request - rule can be created on next update
        logger.warning(
            "Failed to create EventBridge rule",
            workflow_id=workflow_id,
            error=str(e),
        )

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

    # Get current workflow to check trigger changes
    current = get_workflow(workflow_id)
    if not current:
        raise NotFoundError(f"Workflow {workflow_id} not found")

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

    # Sync EventBridge rule if trigger changed
    if update_data.trigger is not None:
        try:
            sync_workflow_rule(
                workflow_id=workflow_id,
                old_trigger=current.get("trigger"),
                new_trigger=update_data.trigger,
            )
        except Exception as e:
            # Log but don't fail the request
            logger.warning(
                "Failed to sync EventBridge rule",
                workflow_id=workflow_id,
                error=str(e),
            )

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

    # Get workflow first to check trigger type
    workflow = get_workflow(workflow_id)
    if not workflow:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    # Delete from DynamoDB
    deleted = delete_workflow(workflow_id)

    if not deleted:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    logger.info("Workflow deleted", workflow_id=workflow_id)

    # Clean up EventBridge rule if cron trigger
    if workflow.get("trigger", {}).get("type") == "cron":
        try:
            delete_schedule_rule(workflow_id)
        except Exception as e:
            # Log but don't fail - rule deletion is best effort
            logger.warning(
                "Failed to delete EventBridge rule",
                workflow_id=workflow_id,
                error=str(e),
            )

    return {"message": f"Workflow {workflow_id} deleted", "workflow_id": workflow_id}


# -----------------------------------------------------------------------------
# Execution Routes
# -----------------------------------------------------------------------------


@app.post("/workflows/<workflow_id>/execute")
@tracer.capture_method
def execute_workflow_handler(workflow_id: str) -> dict:
    """Queue a manual workflow execution.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Execution queued confirmation with status

    Raises:
        NotFoundError: If workflow doesn't exist
        BadRequestError: If workflow is disabled or queue unavailable
    """
    logger.info("Queueing workflow execution", workflow_id=workflow_id)

    # Verify workflow exists
    workflow = get_workflow(workflow_id)
    if not workflow:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    # Check if workflow is enabled
    if not workflow.get("enabled", True):
        raise BadRequestError(f"Workflow {workflow_id} is disabled")

    # Check queue URL is configured
    if not EXECUTION_QUEUE_URL:
        logger.error("EXECUTION_QUEUE_URL not configured")
        raise BadRequestError("Execution queue not configured")

    # Get optional trigger data from request body
    body = app.current_event.json_body or {}
    trigger_data = body.get("trigger_data", {})

    # Send message to SQS queue
    message = {
        "workflow_id": workflow_id,
        "trigger_type": "manual",
        "trigger_data": trigger_data,
    }

    try:
        sqs_client.send_message(
            QueueUrl=EXECUTION_QUEUE_URL,
            MessageBody=json.dumps(message),
        )
    except Exception as e:
        logger.exception("Failed to queue execution", error=str(e))
        raise BadRequestError(f"Failed to queue execution: {str(e)}")

    logger.info("Execution queued", workflow_id=workflow_id)

    return {
        "status": "queued",
        "workflow_id": workflow_id,
        "message": "Execution queued successfully",
    }


@app.get("/workflows/<workflow_id>/executions")
@tracer.capture_method
def list_executions_handler(workflow_id: str) -> dict:
    """List executions for a workflow.

    Supports pagination via query parameters:
    - limit: Number of results (default 20, max 100)
    - last_key: Last execution_id for pagination

    Args:
        workflow_id: The workflow identifier

    Returns:
        Object with executions array, count, and pagination info

    Raises:
        NotFoundError: If workflow doesn't exist
    """
    logger.info("Listing executions", workflow_id=workflow_id)

    # Verify workflow exists
    workflow = get_workflow(workflow_id)
    if not workflow:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    # Get pagination params
    params = app.current_event.query_string_parameters or {}
    limit = min(int(params.get("limit", "20")), 100)
    last_key = params.get("last_key")

    # Query executions
    result = list_executions(workflow_id, limit=limit, last_key=last_key)

    return {
        "executions": result["items"],
        "count": len(result["items"]),
        "last_key": result.get("last_key"),
    }


@app.get("/workflows/<workflow_id>/executions/<execution_id>")
@tracer.capture_method
def get_execution_handler(workflow_id: str, execution_id: str) -> dict:
    """Get a single execution by ID.

    Args:
        workflow_id: The workflow identifier
        execution_id: The execution identifier

    Returns:
        Full execution record with step details

    Raises:
        NotFoundError: If execution doesn't exist
    """
    logger.info(
        "Getting execution",
        workflow_id=workflow_id,
        execution_id=execution_id,
    )

    execution = get_execution(workflow_id, execution_id)

    if not execution:
        raise NotFoundError(f"Execution {execution_id} not found")

    return execution


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
