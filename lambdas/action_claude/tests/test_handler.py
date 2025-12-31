"""Unit tests for Claude action Lambda handler."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory and lambdas directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from handler import (
    handler,
    execute_claude,
    ALLOWED_MODELS,
    DEFAULT_MODEL,
    DEFAULT_MAX_TOKENS,
)


class TestExecuteClaude:
    """Tests for execute_claude function."""

    @patch("handler.Anthropic")
    def test_successful_api_call(self, mock_anthropic_class):
        """Test successful Claude API call."""
        # Setup mock
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="This is the AI response.")]
        mock_message.model = "claude-3-haiku-20240307"
        mock_message.usage.input_tokens = 50
        mock_message.usage.output_tokens = 20
        mock_client.messages.create.return_value = mock_message

        config = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 500,
            "prompt": "Summarize: {{trigger.content}}",
        }
        context = {
            "trigger": {"content": "Hello world"},
            "steps": {},
            "secrets": {"anthropic_api_key": "sk-test-key"},
        }

        result = execute_claude(config, context)

        assert result["response"] == "This is the AI response."
        assert result["model"] == "claude-3-haiku-20240307"
        assert result["usage"]["input_tokens"] == 50
        assert result["usage"]["output_tokens"] == 20
        assert result["truncated"] is False

        # Verify API was called correctly
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-3-haiku-20240307"
        assert call_args.kwargs["max_tokens"] == 500
        assert "Hello world" in call_args.kwargs["messages"][0]["content"]

    @patch("handler.Anthropic")
    def test_prompt_interpolation(self, mock_anthropic_class):
        """Test that variables are interpolated in prompt."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Response")]
        mock_message.model = "claude-3-haiku-20240307"
        mock_message.usage.input_tokens = 10
        mock_message.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_message

        config = {
            "prompt": "Title: {{trigger.title}}, Author: {{trigger.author}}",
        }
        context = {
            "trigger": {"title": "My Article", "author": "John"},
            "steps": {},
            "secrets": {"anthropic_api_key": "sk-test"},
        }

        execute_claude(config, context)

        call_args = mock_client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "Title: My Article" in prompt
        assert "Author: John" in prompt

    @patch("handler.Anthropic")
    def test_truncation(self, mock_anthropic_class):
        """Test that long inputs are truncated."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Response")]
        mock_message.model = "claude-3-haiku-20240307"
        mock_message.usage.input_tokens = 100
        mock_message.usage.output_tokens = 10
        mock_client.messages.create.return_value = mock_message

        # Create a very long content
        long_content = "x" * 10000
        config = {
            "prompt": "{{trigger.content}}",
            "truncate_input": 100,
        }
        context = {
            "trigger": {"content": long_content},
            "steps": {},
            "secrets": {"anthropic_api_key": "sk-test"},
        }

        result = execute_claude(config, context)

        assert result["truncated"] is True
        # Verify the prompt was truncated
        call_args = mock_client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert len(prompt) == 100

    def test_missing_api_key(self):
        """Test error when API key is not in secrets."""
        config = {"prompt": "Hello"}
        context = {
            "trigger": {},
            "steps": {},
            "secrets": {},  # No API key
        }

        with pytest.raises(ValueError) as exc_info:
            execute_claude(config, context)

        assert "API key not found in secrets" in str(exc_info.value)
        assert "anthropic_api_key" in str(exc_info.value)

    def test_invalid_model(self):
        """Test error when model is not in allowed list."""
        config = {
            "model": "claude-invalid-model",
            "prompt": "Hello",
        }
        context = {
            "trigger": {},
            "steps": {},
            "secrets": {"anthropic_api_key": "sk-test"},
        }

        with pytest.raises(ValueError) as exc_info:
            execute_claude(config, context)

        assert "Invalid model" in str(exc_info.value)
        assert "claude-invalid-model" in str(exc_info.value)

    @patch("handler.Anthropic")
    def test_custom_api_key_secret(self, mock_anthropic_class):
        """Test using a custom API key secret name."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Response")]
        mock_message.model = "claude-3-haiku-20240307"
        mock_message.usage.input_tokens = 10
        mock_message.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_message

        config = {
            "prompt": "Hello",
            "api_key_secret": "my_custom_key",
        }
        context = {
            "trigger": {},
            "steps": {},
            "secrets": {"my_custom_key": "sk-custom-test"},
        }

        execute_claude(config, context)

        # Verify the custom key was used
        mock_anthropic_class.assert_called_once()
        assert mock_anthropic_class.call_args.kwargs["api_key"] == "sk-custom-test"

    @patch("handler.Anthropic")
    def test_defaults_applied(self, mock_anthropic_class):
        """Test that defaults are applied when config is minimal."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Response")]
        mock_message.model = DEFAULT_MODEL
        mock_message.usage.input_tokens = 10
        mock_message.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_message

        config = {"prompt": "Hello"}
        context = {
            "trigger": {},
            "steps": {},
            "secrets": {"anthropic_api_key": "sk-test"},
        }

        execute_claude(config, context)

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == DEFAULT_MODEL
        assert call_args.kwargs["max_tokens"] == DEFAULT_MAX_TOKENS


class TestHandler:
    """Tests for Lambda handler function."""

    @patch("handler.execute_claude")
    def test_handler_success(self, mock_execute):
        """Test handler returns success status on successful execution."""
        mock_execute.return_value = {
            "response": "AI response",
            "model": "claude-3-haiku-20240307",
            "usage": {"input_tokens": 50, "output_tokens": 20},
            "truncated": False,
        }

        event = {
            "step": {
                "step_id": "step_1",
                "name": "Summarize",
                "type": "claude",
                "config": {"prompt": "Hello"},
            },
            "context": {
                "trigger": {},
                "steps": {},
                "secrets": {"anthropic_api_key": "sk-test"},
            },
            "execution_id": "ex_123",
            "workflow_id": "wf_456",
        }

        result = handler(event, MagicMock())

        assert result["status"] == "success"
        assert result["output"]["response"] == "AI response"
        assert result["error"] is None
        assert "duration_ms" in result

    @patch("handler.execute_claude")
    def test_handler_interpolation_error(self, mock_execute):
        """Test handler returns failed status on interpolation error."""
        from shared.interpolation import InterpolationError

        mock_execute.side_effect = InterpolationError("trigger.missing", "Key not found")

        event = {
            "step": {
                "step_id": "step_1",
                "config": {"prompt": "{{trigger.missing}}"},
            },
            "context": {"trigger": {}, "steps": {}, "secrets": {"anthropic_api_key": "sk-test"}},
            "execution_id": "ex_123",
        }

        result = handler(event, MagicMock())

        assert result["status"] == "failed"
        assert "interpolation failed" in result["error"].lower()

    @patch("handler.execute_claude")
    def test_handler_value_error(self, mock_execute):
        """Test handler returns failed status on ValueError."""
        mock_execute.side_effect = ValueError("Invalid model")

        event = {
            "step": {"step_id": "step_1", "config": {"prompt": "Hello"}},
            "context": {"trigger": {}, "steps": {}, "secrets": {}},
            "execution_id": "ex_123",
        }

        result = handler(event, MagicMock())

        assert result["status"] == "failed"
        assert "Invalid model" in result["error"]

    @patch("handler.execute_claude")
    def test_handler_rate_limit(self, mock_execute):
        """Test handler handles rate limit errors."""
        from anthropic import RateLimitError

        mock_execute.side_effect = RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429),
            body=None,
        )

        event = {
            "step": {"step_id": "step_1", "config": {"prompt": "Hello"}},
            "context": {"trigger": {}, "steps": {}, "secrets": {"anthropic_api_key": "sk-test"}},
            "execution_id": "ex_123",
        }

        result = handler(event, MagicMock())

        assert result["status"] == "failed"
        assert "rate limited" in result["error"].lower()

    @patch("handler.execute_claude")
    def test_handler_timeout(self, mock_execute):
        """Test handler handles timeout errors."""
        from anthropic import APITimeoutError

        mock_execute.side_effect = APITimeoutError(request=MagicMock())

        event = {
            "step": {"step_id": "step_1", "config": {"prompt": "Hello"}},
            "context": {"trigger": {}, "steps": {}, "secrets": {"anthropic_api_key": "sk-test"}},
            "execution_id": "ex_123",
        }

        result = handler(event, MagicMock())

        assert result["status"] == "failed"
        assert "timed out" in result["error"].lower()

    @patch("handler.execute_claude")
    def test_handler_api_error_5xx(self, mock_execute):
        """Test handler handles 5xx API errors."""
        from anthropic import APIError

        mock_execute.side_effect = APIError(
            message="Server error",
            request=MagicMock(),
            body=None,
        )
        mock_execute.side_effect.status_code = 500

        event = {
            "step": {"step_id": "step_1", "config": {"prompt": "Hello"}},
            "context": {"trigger": {}, "steps": {}, "secrets": {"anthropic_api_key": "sk-test"}},
            "execution_id": "ex_123",
        }

        result = handler(event, MagicMock())

        assert result["status"] == "failed"
        assert "try again later" in result["error"].lower()

    @patch("handler.execute_claude")
    def test_handler_api_error_4xx(self, mock_execute):
        """Test handler handles 4xx API errors with message."""
        from anthropic import APIError

        mock_execute.side_effect = APIError(
            message="Bad request: invalid format",
            request=MagicMock(),
            body=None,
        )
        mock_execute.side_effect.status_code = 400

        event = {
            "step": {"step_id": "step_1", "config": {"prompt": "Hello"}},
            "context": {"trigger": {}, "steps": {}, "secrets": {"anthropic_api_key": "sk-test"}},
            "execution_id": "ex_123",
        }

        result = handler(event, MagicMock())

        assert result["status"] == "failed"
        assert "anthropic api error" in result["error"].lower()


class TestAllowedModels:
    """Tests for model validation."""

    def test_allowed_models_list(self):
        """Test that expected models are in allowed list."""
        assert "claude-3-haiku-20240307" in ALLOWED_MODELS
        assert "claude-3-5-sonnet-20241022" in ALLOWED_MODELS
        assert "claude-3-5-haiku-20241022" in ALLOWED_MODELS

    def test_default_model_is_allowed(self):
        """Test that the default model is in allowed list."""
        assert DEFAULT_MODEL in ALLOWED_MODELS
