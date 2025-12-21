"""Lambda handler for Workflow CRUD API and Execution endpoints.

This module provides the main Lambda handler for API Gateway HTTP API,
implementing workflow CRUD operations and execution management using
AWS Powertools for routing, logging, and tracing.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import boto3
from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, NotFoundError
from pydantic import ValidationError

from models import (
    SecretCreate,
    WorkflowCreate,
    WorkflowUpdate,
    generate_workflow_id,
    get_current_timestamp,
)
from eventbridge import (
    delete_poll_rule,
    delete_schedule_rule,
    sync_workflow_enabled,
    sync_workflow_rule,
)
from repository import (
    create_workflow,
    delete_workflow,
    get_execution,
    get_latest_execution_status,
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

# SSM client for secrets management
ssm_client = boto3.client("ssm")


def convert_decimals(obj: Any) -> Any:
    """Recursively convert Decimal types to int/float for JSON serialization.

    DynamoDB returns Decimal for all numeric types. This function converts them
    to native Python types that json.dumps can serialize.

    Args:
        obj: Any object that may contain Decimal values

    Returns:
        Object with Decimals converted to int (if whole number) or float
    """
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert_decimals(item) for item in obj]
    return obj


ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
SECRETS_PATH = f"/automations/{ENVIRONMENT}/secrets/"


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
    """List all workflows with latest execution status.

    Returns:
        Object with workflows array and count
    """
    logger.info("Listing workflows")

    workflows = list_workflows()

    # Enrich each workflow with latest execution status
    for workflow in workflows:
        workflow_id = workflow.get("workflow_id")
        if workflow_id:
            status = get_latest_execution_status(workflow_id)
            workflow["latest_execution_status"] = status

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

    # Clean up EventBridge rule if cron or poll trigger
    trigger_type = workflow.get("trigger", {}).get("type")
    if trigger_type == "cron":
        try:
            delete_schedule_rule(workflow_id)
        except Exception as e:
            logger.warning(
                "Failed to delete cron EventBridge rule",
                workflow_id=workflow_id,
                error=str(e),
            )
    elif trigger_type == "poll":
        try:
            delete_poll_rule(workflow_id)
        except Exception as e:
            logger.warning(
                "Failed to delete poll EventBridge rule",
                workflow_id=workflow_id,
                error=str(e),
            )

    return {"message": f"Workflow {workflow_id} deleted", "workflow_id": workflow_id}


@app.patch("/workflows/<workflow_id>/enabled")
@tracer.capture_method
def toggle_workflow_enabled(workflow_id: str) -> dict:
    """Toggle workflow enabled/disabled status.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Confirmation with new enabled state

    Raises:
        NotFoundError: If workflow doesn't exist
        BadRequestError: If request body is invalid
    """
    logger.info("Toggling workflow enabled", workflow_id=workflow_id)

    # Get current workflow
    workflow = get_workflow(workflow_id)
    if not workflow:
        raise NotFoundError(f"Workflow {workflow_id} not found")

    # Parse request body
    body = app.current_event.json_body or {}
    if "enabled" not in body:
        raise BadRequestError("Missing 'enabled' field in request body")

    new_enabled = bool(body["enabled"])

    # Update in DynamoDB
    updates = {
        "enabled": new_enabled,
        "updated_at": get_current_timestamp(),
    }
    update_workflow(workflow_id, updates)

    # Sync EventBridge rule state for cron/poll triggers
    try:
        sync_workflow_enabled(
            workflow_id,
            workflow.get("trigger"),
            new_enabled,
        )
    except Exception as e:
        logger.warning(
            "Failed to sync EventBridge rule state",
            workflow_id=workflow_id,
            error=str(e),
        )

    action = "enabled" if new_enabled else "disabled"
    logger.info(f"Workflow {action}", workflow_id=workflow_id)

    return {
        "workflow_id": workflow_id,
        "enabled": new_enabled,
        "message": f"Workflow {action}",
    }


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
        "executions": convert_decimals(result["items"]),
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

    return convert_decimals(execution)


# -----------------------------------------------------------------------------
# Secrets Routes
# -----------------------------------------------------------------------------


def mask_secret_value(value: str) -> str:
    """Mask a secret value, showing only last 4 characters.

    Args:
        value: The full secret value

    Returns:
        Masked string like "****abcd"
    """
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


@app.get("/secrets")
@tracer.capture_method
def list_secrets_handler() -> dict:
    """List all secrets (metadata only, no actual values).

    Returns:
        Object with secrets array and count
    """
    logger.info("Listing secrets")

    secrets = []

    try:
        # Get all parameters under the secrets path
        paginator = ssm_client.get_paginator("get_parameters_by_path")

        for page in paginator.paginate(
            Path=SECRETS_PATH,
            WithDecryption=True,  # Need to decrypt to get last 4 chars
        ):
            for param in page.get("Parameters", []):
                # Extract name from full path
                name = param["Name"].replace(SECRETS_PATH, "")

                # Get secret type from tags (default to "custom")
                secret_type = "custom"
                try:
                    tags_response = ssm_client.list_tags_for_resource(
                        ResourceType="Parameter",
                        ResourceId=param["Name"],
                    )
                    for tag in tags_response.get("TagList", []):
                        if tag["Key"] == "secret_type":
                            secret_type = tag["Value"]
                            break
                except Exception:
                    # If we can't get tags, default to custom
                    pass

                secrets.append({
                    "name": name,
                    "secret_type": secret_type,
                    "masked_value": mask_secret_value(param["Value"]),
                    "created_at": param.get("LastModifiedDate", "").isoformat()
                    if param.get("LastModifiedDate")
                    else "",
                })

    except ClientError as e:
        if e.response["Error"]["Code"] != "ParameterNotFound":
            logger.warning("Error listing secrets", error=str(e))
        # Return empty list on error
        pass
    except Exception as e:
        logger.warning("Error listing secrets", error=str(e))
        # Return empty list on error
        pass

    return {"secrets": secrets, "count": len(secrets)}


@app.post("/secrets")
@tracer.capture_method
def create_secret_handler() -> dict:
    """Create a new secret.

    Returns:
        Created secret metadata

    Raises:
        BadRequestError: If request body is invalid or secret already exists
    """
    logger.info("Creating secret")

    # Parse and validate request body
    try:
        body = app.current_event.json_body or {}
        secret_data = SecretCreate(**body)
    except ValidationError as e:
        logger.warning("Validation failed", errors=str(e.errors()))
        raise BadRequestError(f"Invalid request: {e.errors()}")

    # Build parameter path
    param_name = f"{SECRETS_PATH}{secret_data.name}"

    # Check if secret already exists
    try:
        ssm_client.get_parameter(Name=param_name, WithDecryption=False)
        raise BadRequestError(f"Secret '{secret_data.name}' already exists")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ParameterNotFound":
            raise
        # Good - secret doesn't exist yet
        pass

    # Create the secret
    try:
        ssm_client.put_parameter(
            Name=param_name,
            Value=secret_data.value,
            Type="SecureString",
            Description=f"Secret for automation platform ({secret_data.secret_type})",
            Tags=[
                {"Key": "secret_type", "Value": secret_data.secret_type},
                {"Key": "created_by", "Value": "api"},
            ],
        )
    except Exception as e:
        logger.exception("Failed to create secret", error=str(e))
        raise BadRequestError(f"Failed to create secret: {str(e)}")

    logger.info("Secret created", secret_name=secret_data.name)

    return {
        "name": secret_data.name,
        "secret_type": secret_data.secret_type,
        "masked_value": mask_secret_value(secret_data.value),
        "created_at": get_current_timestamp(),
        "message": "Secret created successfully",
    }


@app.delete("/secrets/<name>")
@tracer.capture_method
def delete_secret_handler(name: str) -> dict:
    """Delete a secret.

    Args:
        name: The secret name

    Returns:
        Confirmation message

    Raises:
        NotFoundError: If secret doesn't exist
    """
    logger.info("Deleting secret", secret_name=name)

    param_name = f"{SECRETS_PATH}{name}"

    # Check if secret exists
    try:
        ssm_client.get_parameter(Name=param_name, WithDecryption=False)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            raise NotFoundError(f"Secret '{name}' not found")
        raise

    # Delete the secret
    try:
        ssm_client.delete_parameter(Name=param_name)
    except Exception as e:
        logger.exception("Failed to delete secret", error=str(e))
        raise BadRequestError(f"Failed to delete secret: {str(e)}")

    logger.info("Secret deleted", secret_name=name)

    return {"message": f"Secret '{name}' deleted", "name": name}


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
