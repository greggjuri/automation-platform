"""Transform action Lambda handler.

Transforms data using templates or mappings with variable interpolation.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from aws_lambda_powertools import Logger, Tracer

# Import shared module (bundled during CDK deployment)
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from shared.interpolation import InterpolationError, interpolate

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="action-transform")
tracer = Tracer(service="action-transform")


@tracer.capture_method
def execute_transform(config: dict, context: dict) -> dict:
    """Execute a transform operation.

    Supports two modes:
    1. Template mode: Single string template with output_key
       {"template": "Hello {{trigger.name}}!", "output_key": "greeting"}

    2. Mapping mode: Object with multiple keys
       {"mapping": {"full_name": "{{trigger.first}} {{trigger.last}}"}}

    Args:
        config: Step configuration with template or mapping
        context: Execution context with trigger, steps, secrets

    Returns:
        Dict with transformed output

    Raises:
        InterpolationError: If variable substitution fails
        ValueError: If config is invalid
    """
    # Check for template mode
    if "template" in config:
        template = config["template"]
        output_key = config.get("output_key", "result")

        logger.info("Executing template transform", output_key=output_key)

        result = interpolate(template, context)
        return {output_key: result}

    # Check for mapping mode
    if "mapping" in config:
        mapping = config["mapping"]

        logger.info("Executing mapping transform", keys=list(mapping.keys()))

        if not isinstance(mapping, dict):
            raise ValueError("Mapping must be a dictionary")

        return interpolate(mapping, context)

    # Invalid config
    raise ValueError("Transform config must include 'template' or 'mapping'")


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda handler for Transform action.

    Expects event format from Step Functions:
    {
        "step": {
            "step_id": "step_1",
            "name": "Format message",
            "type": "transform",
            "config": {
                "template": "Hello {{trigger.name}}!",
                "output_key": "greeting"
            }
            # OR
            "config": {
                "mapping": {
                    "full_name": "{{trigger.first}} {{trigger.last}}",
                    "greeting": "Hello {{trigger.first}}!"
                }
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
        "success": true/false,
        "output": {...},  # Transformed data
        "error": null/string,
        "duration_ms": 123,
        "step_result": {...},  # For storing in execution record
        "step_context": {...}  # For updating context.steps
    }
    """
    step = event.get("step", {})
    exec_context = event.get("context", {})
    step_id = step.get("step_id", "unknown")
    step_config = step.get("config", {})

    logger.info(
        "Processing transform action",
        step_id=step_id,
        execution_id=event.get("execution_id"),
    )

    start_time = time.time()
    result: dict[str, Any] = {
        "success": False,
        "output": None,
        "error": None,
        "duration_ms": 0,
    }

    try:
        output = execute_transform(step_config, exec_context)
        result["success"] = True
        result["output"] = output

    except InterpolationError as e:
        logger.exception("Interpolation error", error=str(e))
        result["error"] = f"Variable interpolation failed: {e.message}"

    except ValueError as e:
        logger.exception("Invalid config", error=str(e))
        result["error"] = f"Invalid transform config: {str(e)}"

    except Exception as e:
        logger.exception("Unexpected error", error=str(e))
        result["error"] = f"Unexpected error: {str(e)}"

    finally:
        result["duration_ms"] = int((time.time() - start_time) * 1000)

    # Build step result for execution record
    result["step_result"] = {
        "step_id": step_id,
        "status": "success" if result["success"] else "failed",
        "duration_ms": result["duration_ms"],
        "output": result["output"],
        "error": result["error"],
    }

    # Build context update for next steps
    result["step_context"] = {
        step_id: {"output": result["output"]}
    }

    logger.info(
        "Transform action completed",
        step_id=step_id,
        success=result["success"],
        duration_ms=result["duration_ms"],
    )

    return result
