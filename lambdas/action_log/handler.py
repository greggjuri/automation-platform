"""Log action Lambda handler.

Logs messages to CloudWatch for workflow debugging.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from aws_lambda_powertools import Logger, Tracer
from shared.interpolation import InterpolationError, interpolate

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="action-log")
tracer = Tracer(service="action-log")


@tracer.capture_method
def execute_log(config: dict, context: dict, execution_id: str, workflow_id: str) -> dict:
    """Execute a log operation.

    Config format:
    {
        "message": "Processing item: {{trigger.id}}",
        "level": "info"  # debug, info, warning, error
    }

    Args:
        config: Step configuration with message and level
        context: Execution context with trigger, steps, secrets
        execution_id: Current execution ID
        workflow_id: Current workflow ID

    Returns:
        Dict with logged message

    Raises:
        InterpolationError: If variable substitution fails
    """
    message = config.get("message", "")
    level = config.get("level", "info").lower()

    # Interpolate the message
    interpolated_message = interpolate(message, context)

    # Log with appropriate level
    # Note: 'message' is a reserved LogRecord field, use 'log_message' instead
    log_data = {
        "workflow_log": True,
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "log_message": interpolated_message,
    }

    if level == "debug":
        logger.debug(interpolated_message, **log_data)
    elif level == "warning":
        logger.warning(interpolated_message, **log_data)
    elif level == "error":
        logger.error(interpolated_message, **log_data)
    else:
        logger.info(interpolated_message, **log_data)

    return {
        "logged": True,
        "message": interpolated_message,
        "level": level,
    }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda handler for Log action.

    Expects event format from Step Functions:
    {
        "step": {
            "step_id": "step_1",
            "name": "Debug log",
            "type": "log",
            "config": {
                "message": "Processing: {{trigger.id}}",
                "level": "info"
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
        "output": {...},  # Log result
        "error": null/string,
        "duration_ms": 123
    }
    """
    step = event.get("step", {})
    exec_context = event.get("context", {})
    step_id = step.get("step_id", "unknown")
    step_config = step.get("config", {})
    execution_id = event.get("execution_id", "unknown")
    workflow_id = event.get("workflow_id", "unknown")

    logger.info(
        "Processing log action",
        step_id=step_id,
        execution_id=execution_id,
    )

    start_time = time.time()
    output = None
    error = None
    status = "failed"

    try:
        output = execute_log(step_config, exec_context, execution_id, workflow_id)
        status = "success"

    except InterpolationError as e:
        logger.exception("Interpolation error", error=str(e))
        error = f"Variable interpolation failed: {e.message}"

    except Exception as e:
        logger.exception("Unexpected error", error=str(e))
        error = f"Unexpected error: {str(e)}"

    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "Log action completed",
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
