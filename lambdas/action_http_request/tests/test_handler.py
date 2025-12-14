"""Tests for HTTP Request action handler."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_context():
    """Create a mock workflow context."""
    return {
        "trigger": {"user_id": "123"},
        "steps": {"previous_step": {"output": "test"}},
        "secrets": {"api_key": "secret123"},
    }


@pytest.fixture
def sample_event(mock_context):
    """Create a sample Step Functions event."""
    return {
        "execution_id": "ex_test123",
        "workflow_id": "wf_test456",
        "step_index": 0,
        "step": {
            "name": "Fetch User",
            "action": "http_request",
            "config": {
                "method": "GET",
                "url": "https://api.example.com/users/{{trigger.user_id}}",
                "headers": {
                    "Authorization": "Bearer {{secrets.api_key}}",
                },
            },
        },
        "context": mock_context,
    }


class TestHTTPRequestAction:
    """Test HTTP request action handler."""

    @patch("handler.requests.request")
    def test_successful_get_request(self, mock_request, sample_event):
        """Test successful GET request."""
        # Import inside test to allow patching
        from handler import handler

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"id": "123", "name": "Test User"}'
        mock_response.json.return_value = {"id": "123", "name": "Test User"}
        mock_request.return_value = mock_response

        result = handler(sample_event, None)

        assert result["status"] == "success"
        assert result["output"]["status_code"] == 200
        assert result["output"]["body"]["id"] == "123"

        # Verify interpolation happened
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "users/123" in call_args.kwargs["url"]
        assert call_args.kwargs["headers"]["Authorization"] == "Bearer secret123"

    @patch("handler.requests.request")
    def test_post_request_with_body(self, mock_request):
        """Test POST request with body."""
        from handler import handler

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.text = '{"created": true}'
        mock_response.json.return_value = {"created": True}
        mock_request.return_value = mock_response

        event = {
            "execution_id": "ex_test123",
            "workflow_id": "wf_test456",
            "step_index": 0,
            "step": {
                "name": "Create Item",
                "action": "http_request",
                "config": {
                    "method": "POST",
                    "url": "https://api.example.com/items",
                    "body": {"name": "{{item_name}}"},
                },
            },
            "context": {
                "trigger": {"item_name": "Test Item"},
                "steps": {},
                "secrets": {},
            },
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["output"]["status_code"] == 201
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args.kwargs["json"]["name"] == "Test Item"

    @patch("handler.requests.request")
    def test_request_timeout(self, mock_request):
        """Test request timeout handling."""
        from handler import handler

        import requests
        mock_request.side_effect = requests.exceptions.Timeout("Request timed out")

        event = {
            "execution_id": "ex_test123",
            "workflow_id": "wf_test456",
            "step_index": 0,
            "step": {
                "name": "Slow Request",
                "action": "http_request",
                "config": {
                    "method": "GET",
                    "url": "https://slow.example.com",
                },
            },
            "context": {"trigger": {}, "steps": {}, "secrets": {}},
        }

        result = handler(event, None)

        assert result["status"] == "error"
        assert "timeout" in result["error"].lower()

    @patch("handler.requests.request")
    def test_non_json_response(self, mock_request):
        """Test handling of non-JSON response."""
        from handler import handler

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.text = "Plain text response"
        mock_response.json.side_effect = ValueError("No JSON")
        mock_request.return_value = mock_response

        event = {
            "execution_id": "ex_test123",
            "workflow_id": "wf_test456",
            "step_index": 0,
            "step": {
                "name": "Text Request",
                "action": "http_request",
                "config": {
                    "method": "GET",
                    "url": "https://text.example.com",
                },
            },
            "context": {"trigger": {}, "steps": {}, "secrets": {}},
        }

        result = handler(event, None)

        assert result["status"] == "success"
        assert result["output"]["body"] == "Plain text response"

    @patch("handler.requests.request")
    def test_http_error_status(self, mock_request):
        """Test handling of HTTP error status codes."""
        from handler import handler

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.text = '{"error": "Not found"}'
        mock_response.json.return_value = {"error": "Not found"}
        mock_request.return_value = mock_response

        event = {
            "execution_id": "ex_test123",
            "workflow_id": "wf_test456",
            "step_index": 0,
            "step": {
                "name": "Missing Resource",
                "action": "http_request",
                "config": {
                    "method": "GET",
                    "url": "https://api.example.com/missing",
                },
            },
            "context": {"trigger": {}, "steps": {}, "secrets": {}},
        }

        result = handler(event, None)

        # Should still succeed (caller decides if 404 is an error)
        assert result["status"] == "success"
        assert result["output"]["status_code"] == 404
