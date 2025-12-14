"""Execution Starter Lambda handler.

Consumes SQS messages and starts Step Functions workflow executions.
"""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING, Any

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.batch import BatchProcessor, EventType, process_partial_response
from aws_lambda_powertools.utilities.batch.types import PartialItemFailureResponse
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord

# Import shared module (bundled during CDK deployment)
import sys
sys.path.insert(0, os.path.dirname(__file__))

from shared.ids import calculate_ttl_timestamp, generate_execution_id, get_current_timestamp

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

WORKFLOWS_TABLE_NAME = os.environ.get("WORKFLOWS_TABLE_NAME", "dev-Workflows")
EXECUTIONS_TABLE_NAME = os.environ.get("EXECUTIONS_TABLE_NAME", "dev-Executions")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")
SSM_SECRETS_PATH = os.environ.get("SSM_SECRETS_PATH", "/automation/dev/secrets")

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="execution-starter")
tracer = Tracer(service="execution-starter")
processor = BatchProcessor(event_type=EventType.SQS)

# -----------------------------------------------------------------------------
# AWS Clients
# -----------------------------------------------------------------------------

dynamodb = boto3.resource("dynamodb")
workflows_table = dynamodb.Table(WORKFLOWS_TABLE_NAME)
executions_table = dynamodb.Table(EXECUTIONS_TABLE_NAME)

sfn_client = boto3.client("stepfunctions")
ssm_client = boto3.client("ssm")

# Secrets cache (5 minute TTL as per PRP)
_secrets_cache: dict[str, Any] = {}
_secrets_cache_time: float = 0
SECRETS_CACHE_TTL = 300  # 5 minutes


# -----------------------------------------------------------------------------
# Repository Functions
# -----------------------------------------------------------------------------


@tracer.capture_method
def get_workflow(workflow_id: str) -> dict | None:
    """Fetch workflow from DynamoDB.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Workflow dict or None if not found
    """
    response = workflows_table.get_item(Key={"workflow_id": workflow_id})
    return response.get("Item")


@tracer.capture_method
def create_execution(
    workflow_id: str,
    execution_id: str,
    trigger_type: str,
    trigger_data: dict,
    workflow_name: str,
) -> dict:
    """Create execution record in DynamoDB.

    Args:
        workflow_id: Associated workflow ID
        execution_id: Unique execution ID
        trigger_type: Type of trigger (manual, webhook, cron, poll)
        trigger_data: Data from trigger event
        workflow_name: Name of the workflow for display

    Returns:
        Created execution record
    """
    timestamp = get_current_timestamp()
    ttl = calculate_ttl_timestamp(days=90)

    item = {
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "workflow_name": workflow_name,
        "status": "pending",
        "trigger_type": trigger_type,
        "trigger_data": trigger_data,
        "steps": [],
        "started_at": timestamp,
        "finished_at": None,
        "error": None,
        "ttl": ttl,
    }

    executions_table.put_item(Item=item)
    logger.info("Created execution record", execution_id=execution_id)

    return item


@tracer.capture_method
def update_execution_status(
    workflow_id: str,
    execution_id: str,
    status: str,
    error: str | None = None,
) -> None:
    """Update execution status in DynamoDB.

    Args:
        workflow_id: Workflow ID
        execution_id: Execution ID
        status: New status (running, success, failed)
        error: Error message if failed
    """
    update_expr = "SET #status = :status, updated_at = :updated_at"
    expr_values: dict[str, Any] = {
        ":status": status,
        ":updated_at": get_current_timestamp(),
    }
    expr_names = {"#status": "status"}

    if status in ("success", "failed"):
        update_expr += ", finished_at = :finished_at"
        expr_values[":finished_at"] = get_current_timestamp()

    if error:
        update_expr += ", #error = :error"
        expr_values[":error"] = error
        expr_names["#error"] = "error"

    executions_table.update_item(
        Key={"workflow_id": workflow_id, "execution_id": execution_id},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_values,
        ExpressionAttributeNames=expr_names,
    )


# -----------------------------------------------------------------------------
# Secrets Resolution
# -----------------------------------------------------------------------------


@tracer.capture_method
def resolve_secrets() -> dict[str, str]:
    """Resolve secrets from SSM Parameter Store.

    Caches secrets for 5 minutes to reduce API calls.

    Returns:
        Dict mapping secret names to values
    """
    global _secrets_cache, _secrets_cache_time

    # Check cache validity
    if _secrets_cache and (time.time() - _secrets_cache_time) < SECRETS_CACHE_TTL:
        logger.debug("Using cached secrets")
        return _secrets_cache

    logger.info("Fetching secrets from SSM", path=SSM_SECRETS_PATH)

    secrets: dict[str, str] = {}

    try:
        paginator = ssm_client.get_paginator("get_parameters_by_path")
        for page in paginator.paginate(
            Path=SSM_SECRETS_PATH,
            WithDecryption=True,
            Recursive=True,
        ):
            for param in page.get("Parameters", []):
                # Extract secret name from path
                # e.g., /automation/dev/secrets/api_key -> api_key
                name = param["Name"].split("/")[-1]
                secrets[name] = param["Value"]

        logger.info("Loaded secrets", count=len(secrets))

    except Exception as e:
        logger.warning("Failed to load secrets", error=str(e))
        # Return empty dict - workflow may not need secrets
        return {}

    # Update cache
    _secrets_cache = secrets
    _secrets_cache_time = time.time()

    return secrets


# -----------------------------------------------------------------------------
# SQS Record Processor
# -----------------------------------------------------------------------------


@tracer.capture_method
def process_record(record: SQSRecord) -> None:
    """Process a single SQS record.

    Args:
        record: SQS record containing execution request

    Raises:
        Exception: If processing fails (will be retried via DLQ)
    """
    # Parse message body
    body = json.loads(record.body)
    workflow_id = body.get("workflow_id")
    trigger_type = body.get("trigger_type", "manual")
    trigger_data = body.get("trigger_data", {})

    logger.info(
        "Processing execution request",
        workflow_id=workflow_id,
        trigger_type=trigger_type,
    )

    # Fetch workflow
    workflow = get_workflow(workflow_id)
    if not workflow:
        logger.error("Workflow not found", workflow_id=workflow_id)
        raise ValueError(f"Workflow {workflow_id} not found")

    # Check if workflow is enabled
    if not workflow.get("enabled", True):
        logger.warning("Workflow is disabled", workflow_id=workflow_id)
        raise ValueError(f"Workflow {workflow_id} is disabled")

    # Generate execution ID
    execution_id = generate_execution_id()
    logger.info("Generated execution ID", execution_id=execution_id)

    # Create execution record
    create_execution(
        workflow_id=workflow_id,
        execution_id=execution_id,
        trigger_type=trigger_type,
        trigger_data=trigger_data,
        workflow_name=workflow.get("name", "Unknown"),
    )

    # Resolve secrets
    secrets = resolve_secrets()

    # Prepare Step Functions input
    sfn_input = {
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "workflow": workflow,
        "trigger_data": trigger_data,
        "context": {
            "trigger": trigger_data,
            "steps": {},
            "secrets": secrets,
        },
    }

    # Start Step Functions execution
    try:
        update_execution_status(workflow_id, execution_id, "running")

        sfn_response = sfn_client.start_sync_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=execution_id,
            input=json.dumps(sfn_input),
        )

        # Check execution status
        sfn_status = sfn_response.get("status")
        if sfn_status == "SUCCEEDED":
            update_execution_status(workflow_id, execution_id, "success")
            logger.info("Execution succeeded", execution_id=execution_id)
        else:
            error_msg = sfn_response.get("error", "Unknown error")
            cause = sfn_response.get("cause", "")
            update_execution_status(
                workflow_id, execution_id, "failed",
                error=f"{error_msg}: {cause}"
            )
            logger.error(
                "Execution failed",
                execution_id=execution_id,
                error=error_msg,
                cause=cause,
            )

    except Exception as e:
        logger.exception("Failed to start Step Functions execution", error=str(e))
        update_execution_status(workflow_id, execution_id, "failed", error=str(e))
        raise


# -----------------------------------------------------------------------------
# Lambda Handler
# -----------------------------------------------------------------------------


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> PartialItemFailureResponse:
    """Lambda entry point for SQS-triggered executions.

    Uses batch processing with partial failure support.

    Args:
        event: SQS event with Records
        context: Lambda context

    Returns:
        Partial item failure response for SQS
    """
    logger.info("Processing execution batch", record_count=len(event.get("Records", [])))

    return process_partial_response(
        event=event,
        record_handler=process_record,
        processor=processor,
        context=context,
    )
