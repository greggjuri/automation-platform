"""Tests for Cron Handler Lambda."""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_lambda_context():
    """Create a mock Lambda context."""
    context = MagicMock()
    context.function_name = "cron-handler"
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:cron-handler"
    context.aws_request_id = "test-request-id"
    return context


@pytest.fixture
def cron_workflow():
    """Create a sample cron workflow from DynamoDB."""
    return {
        "workflow_id": "wf_cron123",
        "name": "Daily Weather",
        "enabled": True,
        "trigger": {
            "type": "cron",
            "config": {
                "schedule": "cron(0 13 * * ? *)",
            },
        },
        "steps": [
            {"step_id": "step_1", "type": "http_request", "config": {}},
        ],
    }


@pytest.fixture
def disabled_workflow():
    """Create a disabled workflow."""
    return {
        "workflow_id": "wf_disabled",
        "name": "Disabled Workflow",
        "enabled": False,
        "trigger": {
            "type": "cron",
            "config": {"schedule": "rate(1 hour)"},
        },
        "steps": [],
    }


@pytest.fixture
def webhook_workflow():
    """Create a webhook workflow (not cron)."""
    return {
        "workflow_id": "wf_webhook123",
        "name": "Webhook Workflow",
        "enabled": True,
        "trigger": {"type": "webhook"},
        "steps": [],
    }


def create_eventbridge_event(
    workflow_id: str,
    scheduled_time: str = "2025-12-17T13:00:00Z",
    source: str = "eventbridge-schedule",
) -> dict:
    """Create a mock EventBridge scheduled event."""
    return {
        "workflow_id": workflow_id,
        "time": scheduled_time,
        "source": source,
    }


class TestCronHandler:
    """Test cron handler Lambda."""

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_valid_workflow_queued(
        self, mock_dynamodb, mock_sqs, cron_workflow, mock_lambda_context
    ):
        """Test that enabled cron workflow queues execution."""
        from handler import handler

        # Setup mocks
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": cron_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_eventbridge_event(workflow_id="wf_cron123")

        result = handler(event, mock_lambda_context)

        assert result["status"] == "queued"
        assert result["workflow_id"] == "wf_cron123"
        assert "execution_id" in result
        assert result["execution_id"].startswith("ex_")

        # Verify SQS message was sent
        mock_sqs.send_message.assert_called_once()

    @patch("handler.dynamodb")
    def test_workflow_not_found(self, mock_dynamodb, mock_lambda_context):
        """Test skipped status for missing workflow."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {}  # No Item
        mock_dynamodb.Table.return_value = mock_table

        event = create_eventbridge_event(workflow_id="wf_nonexistent")

        result = handler(event, mock_lambda_context)

        assert result["status"] == "skipped"
        assert result["reason"] == "workflow_not_found"

    @patch("handler.dynamodb")
    def test_workflow_disabled(
        self, mock_dynamodb, disabled_workflow, mock_lambda_context
    ):
        """Test skipped status for disabled workflow."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": disabled_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_eventbridge_event(workflow_id="wf_disabled")

        result = handler(event, mock_lambda_context)

        assert result["status"] == "skipped"
        assert result["reason"] == "workflow_disabled"

    @patch("handler.dynamodb")
    def test_not_cron_trigger(
        self, mock_dynamodb, webhook_workflow, mock_lambda_context
    ):
        """Test skipped status for non-cron workflow."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": webhook_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_eventbridge_event(workflow_id="wf_webhook123")

        result = handler(event, mock_lambda_context)

        assert result["status"] == "skipped"
        assert result["reason"] == "not_cron_trigger"

    def test_missing_workflow_id(self, mock_lambda_context):
        """Test error status when workflow_id is missing."""
        from handler import handler

        event = {"time": "2025-12-17T13:00:00Z"}  # No workflow_id

        result = handler(event, mock_lambda_context)

        assert result["status"] == "error"
        assert result["reason"] == "missing_workflow_id"

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_trigger_data_structure(
        self, mock_dynamodb, mock_sqs, cron_workflow, mock_lambda_context
    ):
        """Test that trigger data includes schedule and timestamps."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": cron_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_eventbridge_event(
            workflow_id="wf_cron123",
            scheduled_time="2025-12-17T13:00:00Z",
        )

        result = handler(event, mock_lambda_context)

        assert result["status"] == "queued"

        # Verify trigger_data structure in SQS message
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])
        trigger_data = message_body["trigger_data"]

        assert trigger_data["type"] == "cron"
        assert trigger_data["schedule"] == "cron(0 13 * * ? *)"
        assert trigger_data["scheduled_time"] == "2025-12-17T13:00:00Z"
        assert "actual_time" in trigger_data

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_sqs_message_format(
        self, mock_dynamodb, mock_sqs, cron_workflow, mock_lambda_context
    ):
        """Test that SQS message has correct structure."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": cron_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_eventbridge_event(workflow_id="wf_cron123")

        handler(event, mock_lambda_context)

        # Verify SQS message structure
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])

        assert "workflow_id" in message_body
        assert "execution_id" in message_body
        assert "trigger_type" in message_body
        assert "trigger_data" in message_body

        assert message_body["workflow_id"] == "wf_cron123"
        assert message_body["trigger_type"] == "cron"
        assert message_body["execution_id"].startswith("ex_")

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_execution_id_generated(
        self, mock_dynamodb, mock_sqs, cron_workflow, mock_lambda_context
    ):
        """Test that execution_id is generated and returned."""
        from handler import handler

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": cron_workflow}
        mock_dynamodb.Table.return_value = mock_table

        event = create_eventbridge_event(workflow_id="wf_cron123")

        result = handler(event, mock_lambda_context)

        assert "execution_id" in result
        assert result["execution_id"].startswith("ex_")
        # Execution ID should be unique - check reasonable length
        assert len(result["execution_id"]) > 20

    @patch("handler.sqs_client")
    @patch("handler.dynamodb")
    def test_workflow_without_schedule(
        self, mock_dynamodb, mock_sqs, mock_lambda_context
    ):
        """Test handling workflow with missing schedule config."""
        from handler import handler

        workflow_no_schedule = {
            "workflow_id": "wf_no_schedule",
            "name": "No Schedule",
            "enabled": True,
            "trigger": {
                "type": "cron",
                "config": {},  # No schedule
            },
            "steps": [],
        }

        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": workflow_no_schedule}
        mock_dynamodb.Table.return_value = mock_table

        event = create_eventbridge_event(workflow_id="wf_no_schedule")

        result = handler(event, mock_lambda_context)

        # Should still queue - schedule is empty string
        assert result["status"] == "queued"

        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args.kwargs["MessageBody"])
        assert message_body["trigger_data"]["schedule"] == ""


class TestExecutionIdGeneration:
    """Test execution ID generation."""

    def test_generate_execution_id_format(self):
        """Test that execution ID has correct format."""
        from handler import generate_execution_id

        exec_id = generate_execution_id()

        assert exec_id.startswith("ex_")
        # Should be ex_ + 12 hex chars (timestamp) + 10 hex chars (random)
        assert len(exec_id) == 3 + 12 + 10

    def test_generate_execution_id_uniqueness(self):
        """Test that execution IDs are unique."""
        from handler import generate_execution_id

        ids = [generate_execution_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique
