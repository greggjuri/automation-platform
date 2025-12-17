"""Unit tests for secrets management API endpoints."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

# Set up environment before importing handler
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("TABLE_NAME", "test-workflows")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("POWERTOOLS_SERVICE_NAME", "test")
os.environ.setdefault("POWERTOOLS_LOG_LEVEL", "DEBUG")


def make_client_error(code: str) -> ClientError:
    """Create a ClientError with the specified error code."""
    return ClientError(
        {"Error": {"Code": code, "Message": f"Test error: {code}"}},
        "TestOperation",
    )


class TestMaskSecretValue:
    """Tests for the mask_secret_value function."""

    def test_mask_long_value(self):
        """Should mask all but last 4 characters."""
        from handler import mask_secret_value

        result = mask_secret_value("https://discord.com/api/webhooks/123/abcd")
        assert result == "****abcd"

    def test_mask_short_value(self):
        """Should return **** for values 4 chars or less."""
        from handler import mask_secret_value

        assert mask_secret_value("abc") == "****"
        assert mask_secret_value("abcd") == "****"

    def test_mask_exact_four_chars(self):
        """Should return **** for exactly 4 chars."""
        from handler import mask_secret_value

        assert mask_secret_value("test") == "****"

    def test_mask_five_chars(self):
        """Should show last 4 for 5+ chars."""
        from handler import mask_secret_value

        assert mask_secret_value("12345") == "****2345"


class TestListSecrets:
    """Tests for GET /secrets endpoint."""

    @patch("handler.ssm_client")
    def test_list_secrets_empty(self, mock_ssm):
        """Should return empty list when no secrets exist."""
        from handler import list_secrets_handler

        # Mock paginator returning empty results
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Parameters": []}]
        mock_ssm.get_paginator.return_value = mock_paginator

        result = list_secrets_handler()

        assert result == {"secrets": [], "count": 0}

    @patch("handler.ssm_client")
    def test_list_secrets_with_items(self, mock_ssm):
        """Should return secret metadata without full values."""
        from handler import list_secrets_handler

        # Mock parameter data
        mock_param = {
            "Name": "/automations/test/secrets/discord_webhook",
            "Value": "https://discord.com/api/webhooks/123/abcd",
            "LastModifiedDate": datetime(2025, 12, 17, 10, 0, 0, tzinfo=timezone.utc),
        }

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Parameters": [mock_param]}]
        mock_ssm.get_paginator.return_value = mock_paginator

        # Mock tags
        mock_ssm.list_tags_for_resource.return_value = {
            "TagList": [{"Key": "secret_type", "Value": "discord_webhook"}]
        }

        result = list_secrets_handler()

        assert result["count"] == 1
        assert len(result["secrets"]) == 1

        secret = result["secrets"][0]
        assert secret["name"] == "discord_webhook"
        assert secret["secret_type"] == "discord_webhook"
        assert secret["masked_value"] == "****abcd"
        assert "2025-12-17" in secret["created_at"]

    @patch("handler.ssm_client")
    def test_list_secrets_handles_error(self, mock_ssm):
        """Should return empty list on SSM error."""
        from handler import list_secrets_handler

        mock_ssm.get_paginator.side_effect = Exception("SSM error")

        result = list_secrets_handler()

        assert result == {"secrets": [], "count": 0}

    @patch("handler.ssm_client")
    def test_list_secrets_handles_parameter_not_found(self, mock_ssm):
        """Should return empty list when path doesn't exist."""
        from handler import list_secrets_handler

        mock_ssm.get_paginator.side_effect = make_client_error("ParameterNotFound")

        result = list_secrets_handler()

        assert result == {"secrets": [], "count": 0}


class TestCreateSecret:
    """Tests for POST /secrets endpoint."""

    @patch("handler.ssm_client")
    @patch("handler.app")
    def test_create_secret_success(self, mock_app, mock_ssm):
        """Should create secret and return metadata."""
        from handler import create_secret_handler

        # Mock request body
        mock_app.current_event.json_body = {
            "name": "discord_webhook",
            "value": "https://discord.com/api/webhooks/123/abcd",
            "secret_type": "discord_webhook",
        }

        # Mock SSM - parameter doesn't exist (raises ParameterNotFound)
        mock_ssm.get_parameter.side_effect = make_client_error("ParameterNotFound")
        mock_ssm.put_parameter.return_value = {}

        result = create_secret_handler()

        assert result["name"] == "discord_webhook"
        assert result["secret_type"] == "discord_webhook"
        assert result["masked_value"] == "****abcd"
        assert "message" in result
        mock_ssm.put_parameter.assert_called_once()

    @patch("handler.ssm_client")
    @patch("handler.app")
    def test_create_secret_invalid_name(self, mock_app, mock_ssm):
        """Should return 400 for invalid secret name."""
        from aws_lambda_powertools.event_handler.exceptions import BadRequestError

        from handler import create_secret_handler

        mock_app.current_event.json_body = {
            "name": "Invalid Name!",  # Invalid - has spaces and special chars
            "value": "some-value",
            "secret_type": "custom",
        }

        with pytest.raises(BadRequestError):
            create_secret_handler()

    @patch("handler.ssm_client")
    @patch("handler.app")
    def test_create_secret_invalid_type(self, mock_app, mock_ssm):
        """Should return 400 for unknown secret type."""
        from aws_lambda_powertools.event_handler.exceptions import BadRequestError

        from handler import create_secret_handler

        mock_app.current_event.json_body = {
            "name": "my_secret",
            "value": "some-value",
            "secret_type": "unknown_type",  # Invalid type
        }

        with pytest.raises(BadRequestError):
            create_secret_handler()

    @patch("handler.ssm_client")
    @patch("handler.app")
    def test_create_secret_already_exists(self, mock_app, mock_ssm):
        """Should return 400 if secret already exists."""
        from aws_lambda_powertools.event_handler.exceptions import BadRequestError

        from handler import create_secret_handler

        mock_app.current_event.json_body = {
            "name": "discord_webhook",
            "value": "https://discord.com/api/webhooks/123/abcd",
            "secret_type": "discord_webhook",
        }

        # Mock SSM - parameter already exists (get_parameter succeeds)
        mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "existing"}}

        with pytest.raises(BadRequestError) as exc:
            create_secret_handler()

        assert "already exists" in str(exc.value)


class TestDeleteSecret:
    """Tests for DELETE /secrets/{name} endpoint."""

    @patch("handler.ssm_client")
    def test_delete_secret_success(self, mock_ssm):
        """Should delete secret and return confirmation."""
        from handler import delete_secret_handler

        # Mock SSM - parameter exists
        mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "existing"}}
        mock_ssm.delete_parameter.return_value = {}

        result = delete_secret_handler("discord_webhook")

        assert result["name"] == "discord_webhook"
        assert "deleted" in result["message"]
        mock_ssm.delete_parameter.assert_called_once()

    @patch("handler.ssm_client")
    def test_delete_secret_not_found(self, mock_ssm):
        """Should return 404 if secret doesn't exist."""
        from aws_lambda_powertools.event_handler.exceptions import NotFoundError

        from handler import delete_secret_handler

        # Mock SSM - parameter not found
        mock_ssm.get_parameter.side_effect = make_client_error("ParameterNotFound")

        with pytest.raises(NotFoundError):
            delete_secret_handler("nonexistent")
