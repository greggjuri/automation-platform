"""Notify action Lambda handler.

Posts notifications to external services (Discord, etc.) with variable interpolation.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import requests
from aws_lambda_powertools import Logger, Tracer
from shared.interpolation import InterpolationError, interpolate

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="action-notify")
tracer = Tracer(service="action-notify")

# Discord message limits
DISCORD_MAX_MESSAGE_LENGTH = 2000

# Request timeout for external services
REQUEST_TIMEOUT = 30


@tracer.capture_method
def execute_discord_notify(config: dict, context: dict) -> dict[str, Any]:
    """Execute a Discord notification.

    Args:
        config: Step configuration with webhook_url and message
        context: Execution context for interpolation

    Returns:
        Dict with status_code, message_sent, and truncated flag

    Raises:
        InterpolationError: If variable substitution fails
        requests.RequestException: If HTTP request fails
    """
    # Interpolate webhook URL and message
    webhook_url = interpolate(config.get("webhook_url", ""), context)
    message = interpolate(config.get("message", ""), context)

    # Validate webhook URL
    if not webhook_url:
        raise ValueError("webhook_url is required for Discord notify")

    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        logger.warning(
            "Webhook URL does not look like a Discord webhook",
            url_prefix=webhook_url[:50] if len(webhook_url) > 50 else webhook_url,
        )

    # Handle empty message
    if not message:
        message = "(empty message)"

    # Truncate if needed
    truncated = False
    if len(message) > DISCORD_MAX_MESSAGE_LENGTH:
        logger.info(
            "Truncating message",
            original_length=len(message),
            max_length=DISCORD_MAX_MESSAGE_LENGTH,
        )
        message = message[: DISCORD_MAX_MESSAGE_LENGTH - 3] + "..."
        truncated = True

    logger.info(
        "Sending Discord notification",
        message_length=len(message),
        truncated=truncated,
    )

    # Send to Discord webhook (plain text content only for MVP)
    response = requests.post(
        webhook_url,
        json={"content": message},
        timeout=REQUEST_TIMEOUT,
    )

    # Discord returns 204 No Content on success
    success = response.status_code in (200, 204)

    if not success:
        logger.warning(
            "Discord webhook returned non-success status",
            status_code=response.status_code,
            response_text=response.text[:200] if response.text else "",
        )

    return {
        "status_code": response.status_code,
        "message_sent": message[:100] if len(message) > 100 else message,
        "truncated": truncated,
        "success": success,
    }


@tracer.capture_method
def execute_notify(config: dict, context: dict) -> dict[str, Any]:
    """Execute a notification with interpolated values.

    Args:
        config: Step configuration with service, webhook_url, message
        context: Execution context with trigger, steps, secrets

    Returns:
        Dict with notification result details

    Raises:
        InterpolationError: If variable substitution fails
        ValueError: If service is unknown
        requests.RequestException: If HTTP request fails
    """
    service = config.get("service", "discord").lower()

    if service == "discord":
        return execute_discord_notify(config, context)

    raise ValueError(f"Unknown notify service: {service}")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda handler for Notify action.

    Expects event format from Step Functions:
    {
        "step": {
            "step_id": "step_1",
            "name": "Send Discord notification",
            "type": "notify",
            "config": {
                "service": "discord",
                "webhook_url": "{{secrets.discord_webhook}}",
                "message": "New event: {{trigger.payload.title}}"
            }
        },
        "context": {
            "trigger": {...},
            "steps": {...},
            "secrets": {...}
        },
        "execution_id": "ex_...",
        "workflow_id": "wf_..."
    }

    Returns:
    {
        "status": "success" or "failed",
        "output": {...},
        "error": null/string,
        "duration_ms": 123
    }
    """
    step = event.get("step", {})
    exec_context = event.get("context", {})
    step_id = step.get("step_id", "unknown")
    step_config = step.get("config", {})

    logger.info(
        "Processing notify action",
        step_id=step_id,
        execution_id=event.get("execution_id"),
        service=step_config.get("service", "discord"),
    )

    start_time = time.time()
    output = None
    error = None
    status = "failed"

    try:
        output = execute_notify(step_config, exec_context)

        # Check if notification was successful
        if output.get("success", False):
            status = "success"
        else:
            error = f"Notification failed with status {output.get('status_code')}"

    except InterpolationError as e:
        logger.exception("Interpolation error", error=str(e))
        error = f"Variable interpolation failed: {e.message}"

    except requests.Timeout:
        logger.exception("Request timeout")
        error = f"Request timed out after {REQUEST_TIMEOUT}s"

    except requests.RequestException as e:
        logger.exception("Request failed", error=str(e))
        error = f"HTTP request failed: {str(e)}"

    except ValueError as e:
        logger.exception("Configuration error", error=str(e))
        error = str(e)

    except Exception as e:
        logger.exception("Unexpected error", error=str(e))
        error = f"Unexpected error: {str(e)}"

    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "Notify action completed",
        step_id=step_id,
        status=status,
        duration_ms=duration_ms,
    )

    return {
        "status": status,
        "output": output,
        "error": error,
        "duration_ms": duration_ms,
    }
