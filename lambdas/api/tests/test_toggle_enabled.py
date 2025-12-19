"""Tests for PATCH /workflows/{id}/enabled endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestToggleWorkflowEnabled:
    """Tests for toggle workflow enabled endpoint."""

    @patch("handler.update_workflow")
    @patch("handler.get_workflow")
    @patch("handler.app")
    def test_toggle_enabled_to_disabled(self, mock_app, mock_get, mock_update):
        """Test toggling workflow from enabled to disabled."""
        mock_get.return_value = {
            "workflow_id": "wf_test123",
            "name": "Test",
            "enabled": True,
            "trigger": {"type": "manual"},
        }
        mock_update.return_value = True
        mock_app.current_event = MagicMock()
        mock_app.current_event.json_body = {"enabled": False}

        from handler import toggle_workflow_enabled

        response = toggle_workflow_enabled("wf_test123")

        assert response["workflow_id"] == "wf_test123"
        assert response["enabled"] is False
        assert "disabled" in response["message"]
        mock_get.assert_called_once_with("wf_test123")
        mock_update.assert_called_once()

    @patch("handler.update_workflow")
    @patch("handler.get_workflow")
    @patch("handler.app")
    def test_toggle_disabled_to_enabled(self, mock_app, mock_get, mock_update):
        """Test toggling workflow from disabled to enabled."""
        mock_get.return_value = {
            "workflow_id": "wf_test123",
            "name": "Test",
            "enabled": False,
            "trigger": {"type": "webhook"},
        }
        mock_update.return_value = True
        mock_app.current_event = MagicMock()
        mock_app.current_event.json_body = {"enabled": True}

        from handler import toggle_workflow_enabled

        response = toggle_workflow_enabled("wf_test123")

        assert response["workflow_id"] == "wf_test123"
        assert response["enabled"] is True
        assert "enabled" in response["message"]

    @patch("handler.get_workflow")
    def test_toggle_workflow_not_found(self, mock_get):
        """Test toggling non-existent workflow returns 404."""
        from aws_lambda_powertools.event_handler.exceptions import NotFoundError

        mock_get.return_value = None

        from handler import toggle_workflow_enabled

        with pytest.raises(NotFoundError) as exc_info:
            toggle_workflow_enabled("wf_notfound")

        assert "wf_notfound" in str(exc_info.value)

    @patch("handler.get_workflow")
    @patch("handler.app")
    def test_toggle_missing_enabled_field(self, mock_app, mock_get):
        """Test toggling without enabled field returns 400."""
        from aws_lambda_powertools.event_handler.exceptions import BadRequestError

        mock_get.return_value = {
            "workflow_id": "wf_test123",
            "name": "Test",
            "enabled": True,
            "trigger": {"type": "manual"},
        }
        mock_app.current_event = MagicMock()
        mock_app.current_event.json_body = {}  # Missing 'enabled'

        from handler import toggle_workflow_enabled

        with pytest.raises(BadRequestError) as exc_info:
            toggle_workflow_enabled("wf_test123")

        assert "enabled" in str(exc_info.value).lower()

    @patch("handler.disable_schedule_rule")
    @patch("handler.update_workflow")
    @patch("handler.get_workflow")
    @patch("handler.app")
    def test_toggle_cron_workflow_disables_rule(
        self, mock_app, mock_get, mock_update, mock_disable
    ):
        """Test disabling cron workflow also disables EventBridge rule."""
        mock_get.return_value = {
            "workflow_id": "wf_cron123",
            "name": "Cron Test",
            "enabled": True,
            "trigger": {"type": "cron", "config": {"schedule": "rate(1 hour)"}},
        }
        mock_update.return_value = True
        mock_app.current_event = MagicMock()
        mock_app.current_event.json_body = {"enabled": False}

        from handler import toggle_workflow_enabled

        response = toggle_workflow_enabled("wf_cron123")

        assert response["enabled"] is False
        mock_disable.assert_called_once_with("wf_cron123")

    @patch("handler.enable_schedule_rule")
    @patch("handler.update_workflow")
    @patch("handler.get_workflow")
    @patch("handler.app")
    def test_toggle_cron_workflow_enables_rule(
        self, mock_app, mock_get, mock_update, mock_enable
    ):
        """Test enabling cron workflow also enables EventBridge rule."""
        mock_get.return_value = {
            "workflow_id": "wf_cron123",
            "name": "Cron Test",
            "enabled": False,
            "trigger": {"type": "cron", "config": {"schedule": "rate(1 hour)"}},
        }
        mock_update.return_value = True
        mock_app.current_event = MagicMock()
        mock_app.current_event.json_body = {"enabled": True}

        from handler import toggle_workflow_enabled

        response = toggle_workflow_enabled("wf_cron123")

        assert response["enabled"] is True
        mock_enable.assert_called_once_with("wf_cron123")

    @patch("handler.enable_schedule_rule")
    @patch("handler.disable_schedule_rule")
    @patch("handler.update_workflow")
    @patch("handler.get_workflow")
    @patch("handler.app")
    def test_toggle_webhook_workflow_no_eventbridge(
        self, mock_app, mock_get, mock_update, mock_disable, mock_enable
    ):
        """Test toggling webhook workflow does not call EventBridge."""
        mock_get.return_value = {
            "workflow_id": "wf_webhook123",
            "name": "Webhook Test",
            "enabled": True,
            "trigger": {"type": "webhook"},
        }
        mock_update.return_value = True
        mock_app.current_event = MagicMock()
        mock_app.current_event.json_body = {"enabled": False}

        from handler import toggle_workflow_enabled

        response = toggle_workflow_enabled("wf_webhook123")

        assert response["enabled"] is False
        mock_disable.assert_not_called()
        mock_enable.assert_not_called()


class TestEventBridgeFunctions:
    """Tests for EventBridge enable/disable functions."""

    @patch("eventbridge.events_client")
    def test_enable_schedule_rule(self, mock_events):
        """Test enable_schedule_rule calls EventBridge API."""
        from eventbridge import enable_schedule_rule

        enable_schedule_rule("wf_test123")

        mock_events.enable_rule.assert_called_once()
        call_args = mock_events.enable_rule.call_args
        assert "wf_test123" in call_args.kwargs["Name"]

    @patch("eventbridge.events_client")
    def test_disable_schedule_rule(self, mock_events):
        """Test disable_schedule_rule calls EventBridge API."""
        from eventbridge import disable_schedule_rule

        disable_schedule_rule("wf_test123")

        mock_events.disable_rule.assert_called_once()
        call_args = mock_events.disable_rule.call_args
        assert "wf_test123" in call_args.kwargs["Name"]

    @patch("eventbridge.events_client")
    def test_enable_nonexistent_rule(self, mock_events):
        """Test enabling non-existent rule handles gracefully."""
        # Create a proper exception class for the mock
        class ResourceNotFoundException(Exception):
            pass

        mock_events.exceptions.ResourceNotFoundException = ResourceNotFoundException
        mock_events.enable_rule.side_effect = ResourceNotFoundException("Rule not found")

        from eventbridge import enable_schedule_rule

        # Should not raise, just log warning
        enable_schedule_rule("wf_notfound")

    @patch("eventbridge.events_client")
    def test_disable_nonexistent_rule(self, mock_events):
        """Test disabling non-existent rule handles gracefully."""
        # Create a proper exception class for the mock
        class ResourceNotFoundException(Exception):
            pass

        mock_events.exceptions.ResourceNotFoundException = ResourceNotFoundException
        mock_events.disable_rule.side_effect = ResourceNotFoundException("Rule not found")

        from eventbridge import disable_schedule_rule

        # Should not raise, just log warning
        disable_schedule_rule("wf_notfound")
