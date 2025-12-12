"""
Example: Step Functions Action Lambda

This example demonstrates the standard pattern for Lambda functions that
execute as tasks within Step Functions workflows. Use this as a template
for new action types (HTTP request, transform, notify, etc.).

Key patterns:
- Input/output structure for Step Functions state
- Error handling with retryable vs non-retryable errors
- Timeout-aware execution
- Structured logging for debugging workflows

Copy this file and adapt for your specific action type.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any

import httpx
from aws_lambda_powertools import Logger, Tracer
from pydantic import BaseModel, Field, ValidationError

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Timeout for HTTP requests (leave buffer for Lambda timeout)
HTTP_TIMEOUT_SECONDS = int(os.environ.get("HTTP_TIMEOUT_SECONDS", "25"))

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="http-request-action")
tracer = Tracer(service="http-request-action")

# -----------------------------------------------------------------------------
# Custom Exceptions
# -----------------------------------------------------------------------------


class RetryableError(Exception):
    """Error that Step Functions should retry (5xx, network issues)."""

    pass


class NonRetryableError(Exception):
    """Error that should NOT be retried (4xx, validation errors)."""

    pass


# -----------------------------------------------------------------------------
# Pydantic Models
# -----------------------------------------------------------------------------


class ActionInput(BaseModel):
    """Input structure from Step Functions state.

    This model validates the input passed to this action from the workflow.
    The step_id and config come from the workflow definition.
    Previous step outputs are available in the context.
    """

    step_id: str = Field(..., description="Unique identifier for this step")
    config: dict = Field(..., description="Action configuration from workflow")
    context: dict = Field(default_factory=dict, description="Workflow execution context")


class HttpRequestConfig(BaseModel):
    """Configuration specific to HTTP request action."""

    method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    url: str = Field(..., min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = Field(default=None)
    timeout_seconds: int = Field(default=HTTP_TIMEOUT_SECONDS, ge=1, le=30)


class ActionOutput(BaseModel):
    """Output structure returned to Step Functions.

    This model ensures consistent output format for all actions.
    The output is stored in the workflow execution record.
    """

    step_id: str
    status: str  # success | failed
    started_at: str
    finished_at: str
    duration_ms: int
    output: Any = None
    error: str | None = None


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"


def resolve_variables(value: Any, context: dict) -> Any:
    """Resolve template variables in configuration.

    Supports patterns like:
    - {{trigger.field}} - Data from trigger event
    - {{steps.step_id.output}} - Output from previous step
    - {{secrets.name}} - Values from SSM (requires separate lookup)

    Args:
        value: The value to resolve (string, dict, or list)
        context: The workflow execution context

    Returns:
        Value with variables replaced
    """
    if isinstance(value, str):
        # Simple variable replacement
        # In production, use a proper template engine like Jinja2
        import re

        pattern = r"\{\{(\w+)\.([^}]+)\}\}"

        def replace(match):
            namespace = match.group(1)  # e.g., "trigger", "steps"
            path = match.group(2)  # e.g., "title", "step_1.output"

            try:
                if namespace == "trigger":
                    return str(context.get("trigger", {}).get(path, ""))
                elif namespace == "steps":
                    parts = path.split(".")
                    step_output = context.get("steps", {}).get(parts[0], {})
                    for part in parts[1:]:
                        step_output = step_output.get(part, {})
                    return str(step_output) if step_output else ""
                elif namespace == "env":
                    return os.environ.get(path, "")
            except Exception:
                return match.group(0)  # Return original if resolution fails

            return match.group(0)

        return re.sub(pattern, replace, value)

    elif isinstance(value, dict):
        return {k: resolve_variables(v, context) for k, v in value.items()}

    elif isinstance(value, list):
        return [resolve_variables(item, context) for item in value]

    return value


# -----------------------------------------------------------------------------
# Action Implementation
# -----------------------------------------------------------------------------


@tracer.capture_method
def execute_http_request(config: HttpRequestConfig, context: dict) -> dict:
    """Execute an HTTP request action.

    Args:
        config: The HTTP request configuration
        context: Workflow execution context for variable resolution

    Returns:
        Response data (status code, headers, body)

    Raises:
        RetryableError: For 5xx errors or network issues
        NonRetryableError: For 4xx errors or validation failures
    """
    # Resolve any template variables in the config
    resolved_url = resolve_variables(config.url, context)
    resolved_headers = resolve_variables(config.headers, context)
    resolved_body = resolve_variables(config.body, context)

    logger.info(
        "Executing HTTP request",
        method=config.method,
        url=resolved_url,
        has_body=resolved_body is not None,
    )

    try:
        with httpx.Client(timeout=config.timeout_seconds) as client:
            response = client.request(
                method=config.method,
                url=resolved_url,
                headers=resolved_headers,
                json=resolved_body if resolved_body else None,
            )

        # Log response info
        logger.info(
            "HTTP response received",
            status_code=response.status_code,
            content_length=len(response.content),
        )

        # Handle error status codes
        if response.status_code >= 500:
            raise RetryableError(f"Server error: {response.status_code}")
        elif response.status_code >= 400:
            raise NonRetryableError(f"Client error: {response.status_code} - {response.text}")

        # Parse response body
        try:
            body = response.json()
        except json.JSONDecodeError:
            body = response.text

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body,
        }

    except httpx.TimeoutException as e:
        logger.error("HTTP request timed out", error=str(e))
        raise RetryableError(f"Request timed out: {e}")

    except httpx.NetworkError as e:
        logger.error("Network error", error=str(e))
        raise RetryableError(f"Network error: {e}")


# -----------------------------------------------------------------------------
# Lambda Handler
# -----------------------------------------------------------------------------


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda entry point for HTTP request action.

    This handler is invoked by Step Functions as a Task state.
    It receives input from the workflow state and returns output
    to be stored in the execution record.

    Args:
        event: Input from Step Functions containing action config and context
        context: Lambda context (timeout, memory, etc.)

    Returns:
        ActionOutput dict with status, timing, and results
    """
    started_at = get_current_timestamp()
    start_time = datetime.utcnow()

    logger.info("Action started", event=event)

    try:
        # Validate input structure
        try:
            action_input = ActionInput(**event)
        except ValidationError as e:
            raise NonRetryableError(f"Invalid action input: {e}")

        # Validate HTTP config
        try:
            http_config = HttpRequestConfig(**action_input.config)
        except ValidationError as e:
            raise NonRetryableError(f"Invalid HTTP config: {e}")

        # Execute the HTTP request
        result = execute_http_request(http_config, action_input.context)

        # Calculate duration
        finished_at = get_current_timestamp()
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Return success output
        output = ActionOutput(
            step_id=action_input.step_id,
            status="success",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            output=result,
        )

        logger.info("Action completed successfully", duration_ms=duration_ms)
        return output.model_dump()

    except RetryableError as e:
        # These errors should trigger Step Functions retry
        logger.warning("Retryable error", error=str(e))
        raise

    except NonRetryableError as e:
        # These errors should NOT be retried
        logger.error("Non-retryable error", error=str(e))

        finished_at = get_current_timestamp()
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        output = ActionOutput(
            step_id=event.get("step_id", "unknown"),
            status="failed",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            error=str(e),
        )

        return output.model_dump()

    except Exception as e:
        # Unexpected errors - log and re-raise
        logger.exception("Unexpected error", error=str(e))
        raise
