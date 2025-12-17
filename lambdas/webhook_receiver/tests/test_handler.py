"""Tests for Webhook Receiver handler."""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_lambda_context():
    """Create a mock Lambda context."""
    context = MagicMock()
    context.function_name = "webhook-receiver"
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:webhook-receiver"
    context.aws_request_id = "test-request-id"
    return context


@pytest.fixture
def sample_workflow():
    """Create a sample workflow from DynamoDB."""
    return {
        "workflow_id": "wf_test123",
        "name": "Test Workflow",
        "enabled": True,
        "trigger": {"type": "webhook"},
        "steps": [
            {"step_id": "step_1", "type": "transform", "config": {}},
        ],
    }


@pytest.fixture
def disabled_workflow():
    """Create a disabled workflow."""
    return {
        "workflow_id": "wf_disabled",
        "name": "Disabled Workflow",
        "enabled": False,
        "trigger": {"type": "webhook"},
        "steps": [],
    }


def create_api_event(
    workflow_id: str,
    body: str | None = None,
    content_type: str = "application/json",
    query_params: dict | None = None,
    headers: dict | None = None,
) -> dict:
    """Create a mock API Gateway HTTP API event."""
    default_headers = {
        "content-type": content_type,
        "user-agent": "TestClient/1.0",
        "x-github-event": "push",
    }
    if headers:
        default_headers.update(headers)

    return {
        "version": "2.0",
        "routeKey": "POST /webhook/{workflow_id}",
        "rawPath": f"/webhook/{workflow_id}",
        "rawQueryString": "",
        "headers": default_headers,
        "queryStringParameters": query_params,
        "pathParameters": {"workflow_id": workflow_id},
        "body": body,
        "isBase64Encoded": False,
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "testapi",
            "domainName": "test.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "test",
            "http": {
                "method": "POST",
                "path": f"/webhook/{workflow_id}",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "TestClient/1.0",
            },
            "requestId": "test-request-id",
            "routeKey": "POST /webhook/{workflow_id}",
            "stage": "$default",
            "time": "12/Dec/2025:10:00:00 +0000",
            "timeEpoch": 1734001200000,
        },
    }


class TestWebhookReceiver:
    """Test webhook receiver handler."""

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_json_body_parsing(
        self, mock_dynamodb, mock_sqs, sample_workflow, mock_lambda_context
    ):
        """Test that JSON body is correctly parsed."""
        from handler import handler

        # Setup mocks
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": sample_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_api_event(
            workflow_id="wf_test123",
            body=json.dumps({"name": "test", "count": 42}),
            content_type="application/json",
        )

        result = handler(event, mock_lambda_context)
        body = json.loads(result["body"])

        assert result["statusCode"] == 200
        assert body["status"] == "queued"
        assert body["workflow_id"] == "wf_test123"
        assert "execution_id" in body

        # Verify SQS message was sent
        mock_sqs.send_message.assert_called_once()
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])
        assert message_body["trigger_type"] == "webhook"
        assert message_body["trigger_data"]["payload"]["name"] == "test"
        assert message_body["trigger_data"]["payload"]["count"] == 42

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_form_body_parsing(
        self, mock_dynamodb, mock_sqs, sample_workflow, mock_lambda_context
    ):
        """Test that form-urlencoded body is correctly parsed."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": sample_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_api_event(
            workflow_id="wf_test123",
            body="name=test&value=123",
            content_type="application/x-www-form-urlencoded",
        )

        result = handler(event, mock_lambda_context)
        body = json.loads(result["body"])

        assert result["statusCode"] == 200
        assert body["status"] == "queued"

        # Verify form data was parsed
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])
        assert message_body["trigger_data"]["payload"]["name"] == "test"
        assert message_body["trigger_data"]["payload"]["value"] == "123"

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_raw_body_fallback(
        self, mock_dynamodb, mock_sqs, sample_workflow, mock_lambda_context
    ):
        """Test that unknown content types store raw body."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": sample_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_api_event(
            workflow_id="wf_test123",
            body="some raw text",
            content_type="text/plain",
        )

        result = handler(event, mock_lambda_context)

        assert result["statusCode"] == 200

        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])
        assert message_body["trigger_data"]["payload"]["raw"] == "some raw text"

    @patch("handler.dynamodb")
    def test_workflow_not_found(self, mock_dynamodb, mock_lambda_context):
        """Test 404 response for missing workflow."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No Item
        mock_dynamodb.Table.return_value = mock_table

        event = create_api_event(
            workflow_id="wf_nonexistent",
            body="{}",
        )

        result = handler(event, mock_lambda_context)

        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "not found" in body["message"].lower()

    @patch("handler.dynamodb")
    def test_workflow_disabled(
        self, mock_dynamodb, disabled_workflow, mock_lambda_context
    ):
        """Test 400 response for disabled workflow."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": disabled_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_api_event(
            workflow_id="wf_disabled",
            body="{}",
        )

        result = handler(event, mock_lambda_context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "disabled" in body["message"].lower()

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_headers_extracted(
        self, mock_dynamodb, mock_sqs, sample_workflow, mock_lambda_context
    ):
        """Test that relevant headers are included in trigger data."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": sample_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_api_event(
            workflow_id="wf_test123",
            body="{}",
            headers={
                "x-github-event": "push",
                "x-github-delivery": "abc123",
            },
        )

        result = handler(event, mock_lambda_context)
        assert result["statusCode"] == 200

        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])
        headers = message_body["trigger_data"]["headers"]

        # Should include custom headers
        assert headers.get("x-github-event") == "push"
        assert headers.get("x-github-delivery") == "abc123"
        # Should not include AWS-specific headers
        assert "x-amzn-trace-id" not in headers
        assert "host" not in headers

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_query_params_extracted(
        self, mock_dynamodb, mock_sqs, sample_workflow, mock_lambda_context
    ):
        """Test that query parameters are included in trigger data."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": sample_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_api_event(
            workflow_id="wf_test123",
            body="{}",
            query_params={"token": "abc123", "debug": "true"},
        )

        result = handler(event, mock_lambda_context)
        assert result["statusCode"] == 200

        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])
        query = message_body["trigger_data"]["query"]

        assert query["token"] == "abc123"
        assert query["debug"] == "true"

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_sqs_message_format(
        self, mock_dynamodb, mock_sqs, sample_workflow, mock_lambda_context
    ):
        """Test that SQS message has correct structure."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": sample_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_api_event(
            workflow_id="wf_test123",
            body='{"event": "test"}',
        )

        result = handler(event, mock_lambda_context)
        assert result["statusCode"] == 200

        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])

        # Verify message structure
        assert "workflow_id" in message_body
        assert "execution_id" in message_body
        assert "trigger_type" in message_body
        assert "trigger_data" in message_body

        assert message_body["workflow_id"] == "wf_test123"
        assert message_body["trigger_type"] == "webhook"
        assert message_body["execution_id"].startswith("ex_")

        # Verify trigger_data structure
        trigger_data = message_body["trigger_data"]
        assert trigger_data["type"] == "webhook"
        assert "payload" in trigger_data
        assert "headers" in trigger_data
        assert "query" in trigger_data
        assert "method" in trigger_data
        assert "timestamp" in trigger_data

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_execution_id_returned(
        self, mock_dynamodb, mock_sqs, sample_workflow, mock_lambda_context
    ):
        """Test that response includes execution_id."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": sample_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_api_event(
            workflow_id="wf_test123",
            body="{}",
        )

        result = handler(event, mock_lambda_context)
        body = json.loads(result["body"])

        assert "execution_id" in body
        assert body["execution_id"].startswith("ex_")
        # Execution ID should be unique - check it has reasonable length
        assert len(body["execution_id"]) > 20

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_empty_body_handled(
        self, mock_dynamodb, mock_sqs, sample_workflow, mock_lambda_context
    ):
        """Test that empty body is handled gracefully."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": sample_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_api_event(
            workflow_id="wf_test123",
            body=None,
        )

        result = handler(event, mock_lambda_context)
        body = json.loads(result["body"])

        assert result["statusCode"] == 200
        assert body["status"] == "queued"

        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])
        assert message_body["trigger_data"]["payload"] == {}


class TestBodyParsing:
    """Test body parsing functions."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON body."""
        from handler import parse_body

        result = parse_body('{"key": "value"}', "application/json")
        assert result == {"key": "value"}

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON returns raw."""
        from handler import parse_body

        result = parse_body("not json", "application/json")
        assert result == {"raw": "not json"}

    def test_parse_form_urlencoded(self):
        """Test parsing form-urlencoded body."""
        from handler import parse_body

        result = parse_body("a=1&b=2", "application/x-www-form-urlencoded")
        assert result == {"a": "1", "b": "2"}

    def test_parse_form_urlencoded_multi_value(self):
        """Test parsing form-urlencoded with multi-value params."""
        from handler import parse_body

        result = parse_body("a=1&a=2&a=3", "application/x-www-form-urlencoded")
        assert result == {"a": ["1", "2", "3"]}

    def test_parse_unknown_content_type(self):
        """Test unknown content type returns raw."""
        from handler import parse_body

        result = parse_body("raw text", "text/plain")
        assert result == {"raw": "raw text"}

    def test_parse_empty_body(self):
        """Test parsing empty body."""
        from handler import parse_body

        result = parse_body(None, "application/json")
        assert result == {}

        result = parse_body("", "application/json")
        assert result == {}


class TestHeaderExtraction:
    """Test header extraction function."""

    def test_extract_headers_filters_aws(self):
        """Test that AWS headers are filtered out."""
        from handler import extract_headers

        headers = {
            "content-type": "application/json",
            "x-amzn-trace-id": "Root=1-abc123",
            "x-forwarded-for": "1.2.3.4",
            "host": "api.example.com",
            "x-custom-header": "custom-value",
        }

        result = extract_headers(headers)

        assert "content-type" in result
        assert "x-custom-header" in result
        assert "x-amzn-trace-id" not in result
        assert "x-forwarded-for" not in result
        assert "host" not in result

    def test_extract_headers_none(self):
        """Test extracting from None headers."""
        from handler import extract_headers

        result = extract_headers(None)
        assert result == {}

    def test_extract_headers_empty(self):
        """Test extracting from empty headers."""
        from handler import extract_headers

        result = extract_headers({})
        assert result == {}
