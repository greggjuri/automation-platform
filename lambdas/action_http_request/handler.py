"""HTTP Request action Lambda handler.

Executes HTTP requests with variable interpolation for workflow steps.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

import requests
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

logger = Logger(service="action-http-request")
tracer = Tracer(service="action-http-request")

# Maximum response body size to store (256KB)
MAX_RESPONSE_SIZE = 256 * 1024


@tracer.capture_method
def execute_http_request(config: dict, context: dict) -> dict:
    """Execute an HTTP request with interpolated values.

    Args:
        config: Step configuration with method, url, headers, body, timeout
        context: Execution context with trigger, steps, secrets

    Returns:
        Dict with status_code, headers, body from response

    Raises:
        InterpolationError: If variable substitution fails
        requests.RequestException: If HTTP request fails
    """
    # Interpolate all config values
    method = interpolate(config.get("method", "GET"), context).upper()
    url = interpolate(config.get("url", ""), context)
    headers = interpolate(config.get("headers", {}), context)
    body = config.get("body")
    timeout = config.get("timeout_seconds", 30)

    logger.info(
        "Executing HTTP request",
        method=method,
        url=url,
        has_body=body is not None,
    )

    # Prepare request kwargs
    request_kwargs: dict[str, Any] = {
        "method": method,
        "url": url,
        "headers": headers,
        "timeout": timeout,
    }

    # Handle body - interpolate if present
    if body is not None:
        interpolated_body = interpolate(body, context)
        if isinstance(interpolated_body, (dict, list)):
            request_kwargs["json"] = interpolated_body
        else:
            request_kwargs["data"] = str(interpolated_body)

    # Execute request
    response = requests.request(**request_kwargs)

    # Parse response body
    response_body: Any = None
    content_type = response.headers.get("Content-Type", "")

    # Truncate large responses
    if len(response.content) > MAX_RESPONSE_SIZE:
        logger.warning(
            "Response body truncated",
            original_size=len(response.content),
            max_size=MAX_RESPONSE_SIZE,
        )
        truncated = response.content[:MAX_RESPONSE_SIZE]
        response_body = truncated.decode("utf-8", errors="replace")
    elif "application/json" in content_type:
        try:
            response_body = response.json()
        except json.JSONDecodeError:
            response_body = response.text
    else:
        response_body = response.text

    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body": response_body,
    }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda handler for HTTP Request action.

    Expects event format from Step Functions:
    {
        "step": {
            "step_id": "step_1",
            "name": "Fetch data",
            "type": "http_request",
            "config": {
                "method": "GET",
                "url": "https://api.example.com/data",
                "headers": {...},
                "body": {...},
                "timeout_seconds": 30
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
        "output": {...},  # Response data
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
        "Processing HTTP request action",
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
        output = execute_http_request(step_config, exec_context)
        result["success"] = True
        result["output"] = output

        # Check for HTTP error status codes
        if output["status_code"] >= 400:
            result["success"] = False
            result["error"] = f"HTTP {output['status_code']}"

    except InterpolationError as e:
        logger.exception("Interpolation error", error=str(e))
        result["error"] = f"Variable interpolation failed: {e.message}"

    except requests.Timeout as e:
        logger.exception("Request timeout", error=str(e))
        result["error"] = f"Request timed out after {step_config.get('timeout_seconds', 30)}s"

    except requests.RequestException as e:
        logger.exception("Request failed", error=str(e))
        result["error"] = f"HTTP request failed: {str(e)}"

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
        "HTTP request action completed",
        step_id=step_id,
        success=result["success"],
        duration_ms=result["duration_ms"],
    )

    return result
