"""Claude AI action Lambda handler.

Calls the Anthropic Claude API with interpolated prompts for AI-powered workflow steps.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from anthropic import Anthropic, APIError, RateLimitError, APITimeoutError
from aws_lambda_powertools import Logger, Tracer
from shared.interpolation import InterpolationError, interpolate

if TYPE_CHECKING:
    from aws_lambda_powertools.utilities.typing import LambdaContext

# -----------------------------------------------------------------------------
# Powertools Setup
# -----------------------------------------------------------------------------

logger = Logger(service="action-claude")
tracer = Tracer(service="action-claude")

# Allowed models for validation
ALLOWED_MODELS = [
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
]

# Default configuration values
DEFAULT_MODEL = "claude-3-haiku-20240307"
DEFAULT_MAX_TOKENS = 500
DEFAULT_API_KEY_SECRET = "anthropic_api_key"
DEFAULT_TRUNCATE_INPUT = 4000

# Request timeout for Anthropic API
REQUEST_TIMEOUT = 25  # Leave buffer for Lambda overhead


@tracer.capture_method
def execute_claude(config: dict, context: dict) -> dict[str, Any]:
    """Execute a Claude API call with interpolated prompt.

    Args:
        config: Step configuration with model, max_tokens, prompt, etc.
        context: Execution context for interpolation

    Returns:
        Dict with response, model, usage, and truncated flag

    Raises:
        InterpolationError: If variable substitution fails
        ValueError: If configuration is invalid
        APIError: If Anthropic API returns an error
    """
    # Get configuration with defaults
    model = config.get("model", DEFAULT_MODEL)
    max_tokens = config.get("max_tokens", DEFAULT_MAX_TOKENS)
    prompt_template = config.get("prompt", "")
    api_key_secret = config.get("api_key_secret", DEFAULT_API_KEY_SECRET)
    truncate_limit = config.get("truncate_input", DEFAULT_TRUNCATE_INPUT)

    # Validate model
    if model not in ALLOWED_MODELS:
        raise ValueError(
            f"Invalid model: {model}. "
            f"Use one of: {', '.join(ALLOWED_MODELS)}"
        )

    # Get API key from secrets
    secrets = context.get("secrets", {})
    api_key = secrets.get(api_key_secret)

    if not api_key:
        raise ValueError(
            f"API key not found in secrets. "
            f"Add '{api_key_secret}' to the Secrets page."
        )

    # Interpolate prompt template
    prompt = interpolate(prompt_template, context)

    # Truncate if needed
    truncated = False
    if len(prompt) > truncate_limit:
        logger.info(
            "Truncating prompt",
            original_length=len(prompt),
            limit=truncate_limit,
        )
        prompt = prompt[:truncate_limit]
        truncated = True

    logger.info(
        "Calling Claude API",
        model=model,
        max_tokens=max_tokens,
        prompt_length=len(prompt),
        truncated=truncated,
    )

    # Call Anthropic API
    client = Anthropic(api_key=api_key, timeout=REQUEST_TIMEOUT)

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    # Extract response text
    response_text = ""
    if message.content:
        for block in message.content:
            if hasattr(block, "text"):
                response_text += block.text

    return {
        "response": response_text,
        "model": message.model,
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        },
        "truncated": truncated,
    }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda handler for Claude AI action.

    Expects event format from Step Functions:
    {
        "step": {
            "step_id": "step_1",
            "name": "Summarize content",
            "type": "claude",
            "config": {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 500,
                "prompt": "Summarize: {{trigger.content}}",
                "api_key_secret": "anthropic_api_key",
                "truncate_input": 4000
            }
        },
        "context": {
            "trigger": {...},
            "steps": {...},
            "secrets": {"anthropic_api_key": "sk-..."}
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
        "Processing Claude action",
        step_id=step_id,
        execution_id=event.get("execution_id"),
        model=step_config.get("model", DEFAULT_MODEL),
    )

    start_time = time.time()
    output = None
    error = None
    status = "failed"

    try:
        output = execute_claude(step_config, exec_context)
        status = "success"

    except InterpolationError as e:
        logger.exception("Interpolation error", error=str(e))
        error = f"Variable interpolation failed: {e.message}"

    except ValueError as e:
        logger.exception("Configuration error", error=str(e))
        error = str(e)

    except RateLimitError:
        logger.exception("Rate limit error")
        error = "Rate limited by Anthropic API. Try again later."

    except APITimeoutError:
        logger.exception("API timeout")
        error = f"Request timed out after {REQUEST_TIMEOUT}s"

    except APIError as e:
        logger.exception("Anthropic API error", error=str(e))
        if e.status_code and e.status_code >= 500:
            error = "Anthropic API error. Try again later."
        else:
            error = f"Anthropic API error: {str(e)}"

    except Exception as e:
        logger.exception("Unexpected error", error=str(e))
        error = f"Unexpected error: {str(e)}"

    duration_ms = int((time.time() - start_time) * 1000)

    logger.info(
        "Claude action completed",
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
