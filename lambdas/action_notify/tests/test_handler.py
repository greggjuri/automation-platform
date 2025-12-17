"""Tests for Notify action handler."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_context():
    """Create a mock workflow context."""
    return {
        "trigger": {
            "type": "webhook",
            "payload": {"repository": {"name": "test-repo"}, "sender": {"login": "testuser"}},
        },
        "steps": {
            "format": {"output": {"result": "Formatted message from step"}},
        },
        "secrets": {
            "discord_webhook": "https://discord.com/api/webhooks/123456/token",
        },
    }


@pytest.fixture
def sample_event(mock_context):
    """Create a sample Step Functions event."""
    return {
        "execution_id": "ex_test123",
        "workflow_id": "wf_test456",
        "step_index": 0,
        "step": {
            "step_id": "notify_step",
            "name": "Send Discord notification",
            "type": "notify",
            "config": {
                "service": "discord",
                "webhook_url": "{{secrets.discord_webhook}}",
                "message": "New push from {{trigger.payload.sender.login}} to {{trigger.payload.repository.name}}",
            },
        },
        "context": mock_context,
    }


@pytest.fixture
def mock_lambda_context():
    """Create a mock Lambda context."""
    context = MagicMock()
    context.function_name = "action-notify"
    context.memory_limit_in_mb = 256
    context.aws_request_id = "test-request-id"
    return context


class TestNotifyAction:
    """Test notify action handler."""

    @patch("handler.requests.post")
    def test_discord_success(self, mock_post, sample_event, mock_lambda_context):
        """Test successful Discord notification."""
        from handler import handler

        # Mock successful Discord response
        mock_response = MagicMock()
        mock_response.status_code = 204  # Discord returns 204 on success
        mock_response.text = ""
        mock_post.return_value = mock_response

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "success"
        assert result["output"]["status_code"] == 204
        assert result["output"]["success"] is True
        assert result["error"] is None

        # Verify the request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check URL was interpolated
        assert call_args.args[0] == "https://discord.com/api/webhooks/123456/token"

        # Check message was interpolated
        sent_payload = call_args.kwargs["json"]
        assert "testuser" in sent_payload["content"]
        assert "test-repo" in sent_payload["content"]

    @patch("handler.requests.post")
    def test_message_truncation(self, mock_post, sample_event, mock_lambda_context):
        """Test that long messages are truncated to 2000 chars."""
        from handler import handler

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_post.return_value = mock_response

        # Create a very long message
        sample_event["step"]["config"]["message"] = "A" * 3000

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "success"
        assert result["output"]["truncated"] is True

        # Verify message was truncated
        call_args = mock_post.call_args
        sent_message = call_args.kwargs["json"]["content"]
        assert len(sent_message) <= 2000
        assert sent_message.endswith("...")

    @patch("handler.requests.post")
    def test_variable_interpolation(self, mock_post, sample_event, mock_lambda_context):
        """Test that {{variable}} placeholders are replaced."""
        from handler import handler

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_post.return_value = mock_response

        # Use step output reference
        sample_event["step"]["config"]["message"] = "Step result: {{steps.format.output.result}}"

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "success"

        call_args = mock_post.call_args
        sent_message = call_args.kwargs["json"]["content"]
        assert "Formatted message from step" in sent_message

    @patch("handler.requests.post")
    def test_invalid_webhook_url_empty(self, mock_post, sample_event, mock_lambda_context):
        """Test error handling for empty webhook URL."""
        from handler import handler

        sample_event["step"]["config"]["webhook_url"] = ""
        sample_event["context"]["secrets"] = {}

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "failed"
        assert "webhook_url" in result["error"].lower()
        mock_post.assert_not_called()

    @patch("handler.requests.post")
    def test_network_error(self, mock_post, sample_event, mock_lambda_context):
        """Test handling of network errors."""
        from handler import handler
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "failed"
        assert "request failed" in result["error"].lower() or "network" in result["error"].lower()

    @patch("handler.requests.post")
    def test_discord_rate_limit(self, mock_post, sample_event, mock_lambda_context):
        """Test handling of Discord rate limit (429)."""
        from handler import handler

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = '{"message": "You are being rate limited"}'
        mock_post.return_value = mock_response

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "failed"
        assert result["output"]["status_code"] == 429
        assert result["output"]["success"] is False

    @patch("handler.requests.post")
    def test_discord_error_response(self, mock_post, sample_event, mock_lambda_context):
        """Test handling of Discord error response."""
        from handler import handler

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"message": "Invalid webhook token"}'
        mock_post.return_value = mock_response

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "failed"
        assert result["output"]["status_code"] == 400

    @patch("handler.requests.post")
    def test_request_timeout(self, mock_post, sample_event, mock_lambda_context):
        """Test handling of request timeout."""
        from handler import handler
        import requests

        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "failed"
        assert "timed out" in result["error"].lower()

    @patch("handler.requests.post")
    def test_unknown_service(self, mock_post, sample_event, mock_lambda_context):
        """Test error for unknown notify service."""
        from handler import handler

        sample_event["step"]["config"]["service"] = "slack"  # Not implemented yet

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "failed"
        assert "unknown" in result["error"].lower() or "service" in result["error"].lower()
        mock_post.assert_not_called()

    @patch("handler.requests.post")
    def test_interpolation_error(self, mock_post, sample_event, mock_lambda_context):
        """Test handling of interpolation errors."""
        from handler import handler

        # Reference a non-existent variable
        sample_event["step"]["config"]["message"] = "{{trigger.nonexistent.value}}"

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "failed"
        assert "interpolation" in result["error"].lower()
        mock_post.assert_not_called()

    @patch("handler.requests.post")
    def test_default_service_is_discord(self, mock_post, sample_event, mock_lambda_context):
        """Test that discord is the default service when not specified."""
        from handler import handler

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_post.return_value = mock_response

        # Remove service from config
        del sample_event["step"]["config"]["service"]

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "success"
        mock_post.assert_called_once()

    @patch("handler.requests.post")
    def test_empty_message(self, mock_post, sample_event, mock_lambda_context):
        """Test handling of empty message."""
        from handler import handler

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_post.return_value = mock_response

        sample_event["step"]["config"]["message"] = ""

        result = handler(sample_event, mock_lambda_context)

        assert result["status"] == "success"

        # Should send "(empty message)" placeholder
        call_args = mock_post.call_args
        sent_message = call_args.kwargs["json"]["content"]
        assert sent_message == "(empty message)"

    @patch("handler.requests.post")
    def test_duration_tracked(self, mock_post, sample_event, mock_lambda_context):
        """Test that duration_ms is tracked."""
        from handler import handler

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_post.return_value = mock_response

        result = handler(sample_event, mock_lambda_context)

        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], int)
        assert result["duration_ms"] >= 0


class TestExecuteDiscordNotify:
    """Test Discord-specific notification logic."""

    @patch("handler.requests.post")
    def test_webhook_url_warning_for_non_discord(self, mock_post):
        """Test that non-Discord URLs generate a warning (but still work)."""
        from handler import execute_discord_notify

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_post.return_value = mock_response

        config = {
            "webhook_url": "https://some-other-service.com/webhook",
            "message": "test",
        }
        context = {"trigger": {}, "steps": {}, "secrets": {}}

        # Should still work despite not being a Discord URL
        result = execute_discord_notify(config, context)
        assert result["status_code"] == 200
        mock_post.assert_called_once()

    @patch("handler.requests.post")
    def test_message_truncation_preserves_ellipsis(self, mock_post):
        """Test that truncation adds proper ellipsis."""
        from handler import execute_discord_notify

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_post.return_value = mock_response

        config = {
            "webhook_url": "https://discord.com/api/webhooks/123/token",
            "message": "X" * 2500,  # Longer than 2000 char limit
        }
        context = {"trigger": {}, "steps": {}, "secrets": {}}

        result = execute_discord_notify(config, context)

        call_args = mock_post.call_args
        sent_message = call_args.kwargs["json"]["content"]

        assert len(sent_message) == 2000
        assert sent_message.endswith("...")
        assert result["truncated"] is True
