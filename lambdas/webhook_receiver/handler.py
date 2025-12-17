"""Webhook Receiver Lambda handler.

Receives webhook requests and queues workflow executions.
Handles JSON, form-urlencoded, and raw body types.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError, NotFoundError
from pydantic import BaseModel

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="webhook-receiver")
tracer = Tracer(service="webhook-receiver")
app = APIGatewayHttpResolver()

# AWS clients
dynamodb = boto3.resource("dynamodb")
sqs_client = boto3.client("sqs")

# Environment variables
WORKFLOWS_TABLE_NAME = os.environ.get("WORKFLOWS_TABLE_NAME", "dev-Workflows")
EXECUTION_QUEUE_URL = os.environ.get("EXECUTION_QUEUE_URL", "")

# Headers to exclude from trigger data (AWS-specific)
EXCLUDED_HEADERS = {
    "x-amzn-trace-id",
    "x-forwarded-for",
    "x-forwarded-port",
    "x-forwarded-proto",
    "x-amz-cf-id",
    "x-amz-date",
    "x-amz-security-token",
    "host",
    "connection",
    "content-length",
}


class WebhookResponse(BaseModel):
    """Response model for webhook endpoint."""

    execution_id: str
    status: str = "queued"
    workflow_id: str


def generate_execution_id() -> str:
    """Generate a ULID-style execution ID.

    Returns:
        Execution ID with 'ex_' prefix
    """
    import time

    # Use timestamp + random for uniqueness (simplified ULID)
    timestamp = int(time.time() * 1000)
    import random

    random_part = random.randint(0, 0xFFFFFFFFFF)
    return f"ex_{timestamp:012x}{random_part:010x}"


def parse_body(raw_body: str | None, content_type: str) -> dict[str, Any]:
    """Parse request body based on content type.

    Args:
        raw_body: Raw request body string
        content_type: Content-Type header value

    Returns:
        Parsed body as dict, or empty dict if no body
    """
    if not raw_body:
        return {}

    content_type = content_type.lower() if content_type else ""

    # JSON body
    if "application/json" in content_type:
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON body, storing as raw")
            return {"raw": raw_body}

    # Form-urlencoded body
    if "application/x-www-form-urlencoded" in content_type:
        try:
            parsed = parse_qs(raw_body, keep_blank_values=True)
            # Flatten single-value lists
            return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        except Exception:
            logger.warning("Failed to parse form body, storing as raw")
            return {"raw": raw_body}

    # Default: store as raw
    return {"raw": raw_body}


def extract_headers(headers: dict[str, str] | None) -> dict[str, str]:
    """Extract relevant headers, excluding AWS-specific ones.

    Args:
        headers: All request headers

    Returns:
        Filtered headers dict
    """
    if not headers:
        return {}

    return {
        k: v
        for k, v in headers.items()
        if k.lower() not in EXCLUDED_HEADERS
    }


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
        trigger_data: Webhook trigger data
    """
    message = {
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "trigger_type": "webhook",
        "trigger_data": trigger_data,
    }

    sqs_client.send_message(
        QueueUrl=EXECUTION_QUEUE_URL,
        MessageBody=json.dumps(message),
    )


@app.post("/webhook/<workflow_id>")
@tracer.capture_method
def receive_webhook(workflow_id: str) -> dict:
    """Receive webhook and queue workflow execution.

    Args:
        workflow_id: The workflow to trigger

    Returns:
        Response with execution_id and status

    Raises:
        NotFoundError: If workflow doesn't exist
        BadRequestError: If workflow is disabled
    """
    logger.info("Webhook received", workflow_id=workflow_id)

    # Validate workflow exists
    workflow = get_workflow(workflow_id)
    if not workflow:
        logger.warning("Workflow not found", workflow_id=workflow_id)
        raise NotFoundError(f"Workflow {workflow_id} not found")

    # Check if workflow is enabled
    if not workflow.get("enabled", True):
        logger.warning("Workflow disabled", workflow_id=workflow_id)
        raise BadRequestError(f"Workflow {workflow_id} is disabled")

    # Parse request body
    content_type = app.current_event.headers.get("content-type", "")
    raw_body = app.current_event.body
    payload = parse_body(raw_body, content_type)

    # Extract headers and query params
    headers = extract_headers(dict(app.current_event.headers or {}))
    query_params = dict(app.current_event.query_string_parameters or {})

    # Build trigger data
    trigger_data = {
        "type": "webhook",
        "payload": payload,
        "headers": headers,
        "query": query_params,
        "method": "POST",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Generate execution ID and queue
    execution_id = generate_execution_id()

    logger.info(
        "Queueing webhook execution",
        workflow_id=workflow_id,
        execution_id=execution_id,
        has_payload=bool(payload),
    )

    queue_execution(workflow_id, execution_id, trigger_data)

    # Return 202 Accepted response
    return {
        "execution_id": execution_id,
        "status": "queued",
        "workflow_id": workflow_id,
    }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda entry point.

    Args:
        event: API Gateway HTTP API event
        context: Lambda context

    Returns:
        API Gateway HTTP API response
    """
    return app.resolve(event, context)
