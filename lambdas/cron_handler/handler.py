"""Cron Handler Lambda for scheduled workflow triggers.

Invoked by EventBridge rules on schedule. Validates the workflow
exists and is enabled, then queues an execution to SQS.
"""

from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import boto3
from aws_lambda_powertools import Logger, Tracer

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="cron-handler")
tracer = Tracer(service="cron-handler")

# AWS clients
dynamodb = boto3.resource("dynamodb")
sqs_client = boto3.client("sqs")

# Environment variables
WORKFLOWS_TABLE_NAME = os.environ.get("WORKFLOWS_TABLE_NAME", "dev-Workflows")
EXECUTION_QUEUE_URL = os.environ.get("EXECUTION_QUEUE_URL", "")


def generate_execution_id() -> str:
    """Generate a ULID-style execution ID.

    Returns:
        Execution ID with 'ex_' prefix
    """
    timestamp = int(time.time() * 1000)
    random_part = random.randint(0, 0xFFFFFFFFFF)
    return f"ex_{timestamp:012x}{random_part:010x}"


@tracer.capture_method
def get_workflow(workflow_id: str) -> dict | None:
    """Fetch workflow from DynamoDB.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Workflow dict or None if not found
    """
    table = dynamodb.Table(WORKFLOWS_TABLE_NAME)
    response = table.get_item(Key={"workflow_id": workflow_id})
    return response.get("Item")


@tracer.capture_method
def queue_execution(
    workflow_id: str,
    execution_id: str,
    trigger_data: dict,
) -> None:
    """Send execution request to SQS queue.

    Args:
        workflow_id: Workflow identifier
        execution_id: Generated execution ID
        trigger_data: Cron trigger data
    """
    message = {
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "trigger_type": "cron",
        "trigger_data": trigger_data,
    }

    sqs_client.send_message(
        QueueUrl=EXECUTION_QUEUE_URL,
        MessageBody=json.dumps(message),
    )


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Handle EventBridge scheduled invocation.

    EventBridge invokes this Lambda on schedule with the workflow_id
    in the event payload. The handler validates the workflow exists
    and is enabled before queueing an execution.

    Args:
        event: EventBridge event with workflow_id and time
        context: Lambda context

    Returns:
        Status dict with execution_id or skip reason
    """
    workflow_id = event.get("workflow_id")
    scheduled_time = event.get("time")  # EventBridge provides this
    source = event.get("source", "eventbridge-schedule")

    logger.info(
        "Cron trigger received",
        workflow_id=workflow_id,
        scheduled_time=scheduled_time,
        source=source,
    )

    # Validate workflow_id is provided
    if not workflow_id:
        logger.error("No workflow_id in event")
        return {"status": "error", "reason": "missing_workflow_id"}

    # Validate workflow exists
    workflow = get_workflow(workflow_id)
    if not workflow:
        logger.warning("Workflow not found", workflow_id=workflow_id)
        return {"status": "skipped", "reason": "workflow_not_found"}

    # Check if workflow is enabled
    if not workflow.get("enabled", True):
        logger.info("Workflow disabled, skipping", workflow_id=workflow_id)
        return {"status": "skipped", "reason": "workflow_disabled"}

    # Verify this is a cron-triggered workflow (safety check)
    trigger = workflow.get("trigger", {})
    if trigger.get("type") != "cron":
        logger.warning(
            "Workflow trigger type is not cron",
            workflow_id=workflow_id,
            trigger_type=trigger.get("type"),
        )
        return {"status": "skipped", "reason": "not_cron_trigger"}

    # Build trigger data
    schedule = trigger.get("config", {}).get("schedule", "")
    trigger_data = {
        "type": "cron",
        "schedule": schedule,
        "scheduled_time": scheduled_time,
        "actual_time": datetime.now(timezone.utc).isoformat(),
    }

    # Generate execution ID and queue
    execution_id = generate_execution_id()

    logger.info(
        "Queueing cron execution",
        workflow_id=workflow_id,
        execution_id=execution_id,
        schedule=schedule,
        trigger_data=trigger_data,  # Debug: log full trigger_data
    )

    queue_execution(workflow_id, execution_id, trigger_data)

    return {
        "status": "queued",
        "execution_id": execution_id,
        "workflow_id": workflow_id,
    }
