"""Tests for Log action handler."""

from unittest.mock import patch

import pytest


@pytest.fixture
def base_event():
    """Create a base Step Functions event."""
    return {
        "execution_id": "ex_test123",
        "workflow_id": "wf_test456",
        "step_index": 0,
        "step": {
            "name": "Log Message",
            "action": "log",
            "config": {},
        },
        "context": {
            "trigger": {"user_id": "123", "action": "signup"},
            "steps": {},
            "secrets": {},
        },
    }


class TestLogAction:
    """Test log action handler."""

    @patch("handler.logger")
    def test_info_log(self, mock_logger, base_event):
        """Test info level logging."""
        from handler import handler

        base_event["step"]["config"] = {
            "message": "User {{trigger.user_id}} performed {{trigger.action}}",
            "level": "info",
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args
        assert "User 123 performed signup" in str(call_args)

    @patch("handler.logger")
    def test_debug_log(self, mock_logger, base_event):
        """Test debug level logging."""
        from handler import handler

        base_event["step"]["config"] = {
            "message": "Debug message",
            "level": "debug",
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        mock_logger.debug.assert_called()

    @patch("handler.logger")
    def test_warning_log(self, mock_logger, base_event):
        """Test warning level logging."""
        from handler import handler

        base_event["step"]["config"] = {
            "message": "Warning message",
            "level": "warning",
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        mock_logger.warning.assert_called()

    @patch("handler.logger")
    def test_error_log(self, mock_logger, base_event):
        """Test error level logging."""
        from handler import handler

        base_event["step"]["config"] = {
            "message": "Error message",
            "level": "error",
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        mock_logger.error.assert_called()

    @patch("handler.logger")
    def test_default_info_level(self, mock_logger, base_event):
        """Test default log level is info."""
        from handler import handler

        base_event["step"]["config"] = {
            "message": "Default level message",
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        mock_logger.info.assert_called()

    @patch("handler.logger")
    def test_log_with_extra_data(self, mock_logger, base_event):
        """Test logging with extra data fields."""
        from handler import handler

        base_event["step"]["config"] = {
            "message": "Action performed",
            "level": "info",
            "data": {
                "user_id": "{{trigger.user_id}}",
                "action": "{{trigger.action}}",
            },
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        assert result["output"]["logged_data"]["user_id"] == "123"
        assert result["output"]["logged_data"]["action"] == "signup"

    @patch("handler.logger")
    def test_log_returns_message(self, mock_logger, base_event):
        """Test that log output includes the message."""
        from handler import handler

        base_event["step"]["config"] = {
            "message": "Test message for user {{trigger.user_id}}",
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        assert result["output"]["message"] == "Test message for user 123"

    def test_interpolation_error(self, base_event):
        """Test error on interpolation failure."""
        from handler import handler

        base_event["step"]["config"] = {
            "message": "Missing: {{nonexistent.path}}",
        }

        result = handler(base_event, None)

        assert result["status"] == "error"
        assert "nonexistent" in result["error"].lower()
