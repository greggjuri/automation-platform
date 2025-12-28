"""Tests for Lambda handler routing and responses."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self):
        """Test health endpoint returns ok."""
        from handler import health_check

        response = health_check()

        assert response == {"status": "ok"}


class TestListWorkflows:
    """Tests for GET /workflows endpoint."""

    @patch("handler.list_workflows")
    def test_list_empty(self, mock_list):
        """Test listing when no workflows exist."""
        mock_list.return_value = []

        from handler import list_workflows_handler

        response = list_workflows_handler()

        assert response == {"workflows": [], "count": 0}
        mock_list.assert_called_once()

    @patch("handler.list_workflows")
    def test_list_with_workflows(self, mock_list, sample_workflow):
        """Test listing with existing workflows."""
        mock_list.return_value = [sample_workflow]

        from handler import list_workflows_handler

        response = list_workflows_handler()

        assert response["count"] == 1
        assert len(response["workflows"]) == 1
        assert response["workflows"][0]["workflow_id"] == "wf_test123"


class TestGetWorkflow:
    """Tests for GET /workflows/{id} endpoint."""

    @patch("handler.get_workflow")
    def test_get_existing(self, mock_get, sample_workflow):
        """Test getting an existing workflow."""
        mock_get.return_value = sample_workflow

        from handler import get_workflow_handler

        response = get_workflow_handler("wf_test123")

        assert response["workflow_id"] == "wf_test123"
        assert response["name"] == "Test Workflow"
        mock_get.assert_called_once_with("wf_test123")

    @patch("handler.get_workflow")
    def test_get_not_found(self, mock_get):
        """Test getting a non-existent workflow."""
        from aws_lambda_powertools.event_handler.exceptions import NotFoundError

        mock_get.return_value = None

        from handler import get_workflow_handler

        with pytest.raises(NotFoundError) as exc_info:
            get_workflow_handler("wf_notfound")

        assert "wf_notfound" in str(exc_info.value)


class TestDeleteWorkflow:
    """Tests for DELETE /workflows/{id} endpoint."""

    @patch("handler.delete_workflow")
    @patch("handler.get_workflow")
    def test_delete_existing(self, mock_get, mock_delete):
        """Test deleting an existing workflow."""
        mock_get.return_value = {
            "workflow_id": "wf_test123",
            "name": "Test Workflow",
            "trigger": {"type": "webhook"},
        }
        mock_delete.return_value = True

        from handler import delete_workflow_handler

        response = delete_workflow_handler("wf_test123")

        assert response["workflow_id"] == "wf_test123"
        assert "deleted" in response["message"].lower()
        mock_delete.assert_called_once_with("wf_test123")

    @patch("handler.delete_workflow")
    @patch("handler.get_workflow")
    def test_delete_not_found(self, mock_get, mock_delete):
        """Test deleting a non-existent workflow."""
        from aws_lambda_powertools.event_handler.exceptions import NotFoundError

        mock_get.return_value = None

        from handler import delete_workflow_handler

        with pytest.raises(NotFoundError) as exc_info:
            delete_workflow_handler("wf_notfound")

        assert "wf_notfound" in str(exc_info.value)
