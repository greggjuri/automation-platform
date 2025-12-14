"""Tests for Transform action handler."""

import pytest


@pytest.fixture
def base_event():
    """Create a base Step Functions event."""
    return {
        "execution_id": "ex_test123",
        "workflow_id": "wf_test456",
        "step_index": 0,
        "step": {
            "name": "Transform Data",
            "action": "transform",
            "config": {},
        },
        "context": {
            "trigger": {"user": {"name": "Alice", "age": 30}},
            "steps": {"fetch": {"output": {"data": [1, 2, 3]}}},
            "secrets": {},
        },
    }


class TestTransformAction:
    """Test transform action handler."""

    def test_template_mode(self, base_event):
        """Test template mode transformation."""
        from handler import handler

        base_event["step"]["config"] = {
            "template": "Hello, {{trigger.user.name}}!",
            "output_key": "greeting",
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        assert result["output"]["greeting"] == "Hello, Alice!"

    def test_mapping_mode(self, base_event):
        """Test mapping mode transformation."""
        from handler import handler

        base_event["step"]["config"] = {
            "mapping": {
                "full_name": "{{trigger.user.name}}",
                "age_text": "Age: {{trigger.user.age}}",
            },
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        assert result["output"]["full_name"] == "Alice"
        assert result["output"]["age_text"] == "Age: 30"

    def test_mapping_with_nested_output(self, base_event):
        """Test mapping with nested structure."""
        from handler import handler

        base_event["step"]["config"] = {
            "mapping": {
                "user_info": {
                    "name": "{{trigger.user.name}}",
                    "profile": {
                        "age": "{{trigger.user.age}}",
                    },
                },
            },
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        assert result["output"]["user_info"]["name"] == "Alice"
        assert result["output"]["user_info"]["profile"]["age"] == "30"

    def test_access_previous_step_output(self, base_event):
        """Test accessing previous step output."""
        from handler import handler

        base_event["step"]["config"] = {
            "template": "Data: {{steps.fetch.output.data | json}}",
            "output_key": "result",
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        assert "[1, 2, 3]" in result["output"]["result"]

    def test_template_with_filters(self, base_event):
        """Test template with filters."""
        from handler import handler

        base_event["step"]["config"] = {
            "template": "{{trigger.user.name | upper}}",
            "output_key": "upper_name",
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        assert result["output"]["upper_name"] == "ALICE"

    def test_missing_variable_error(self, base_event):
        """Test error on missing variable."""
        from handler import handler

        base_event["step"]["config"] = {
            "template": "{{missing.path}}",
            "output_key": "result",
        }

        result = handler(base_event, None)

        assert result["status"] == "error"
        assert "missing" in result["error"].lower()

    def test_missing_config_error(self, base_event):
        """Test error when no template or mapping provided."""
        from handler import handler

        base_event["step"]["config"] = {}

        result = handler(base_event, None)

        assert result["status"] == "error"
        assert "template" in result["error"].lower() or "mapping" in result["error"].lower()

    def test_default_filter_for_missing(self, base_event):
        """Test default filter handles missing values."""
        from handler import handler

        base_event["step"]["config"] = {
            "template": "{{missing | default('fallback')}}",
            "output_key": "result",
        }

        result = handler(base_event, None)

        assert result["status"] == "success"
        assert result["output"]["result"] == "fallback"
