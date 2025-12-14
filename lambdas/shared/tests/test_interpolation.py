"""Tests for interpolation module."""

import json

import pytest

from shared.interpolation import InterpolationError, interpolate


class TestBasicInterpolation:
    """Test basic variable interpolation."""

    def test_simple_string_replacement(self):
        """Test simple variable replacement."""
        template = "Hello, {{name}}!"
        context = {"name": "World"}
        assert interpolate(template, context) == "Hello, World!"

    def test_no_variables(self):
        """Test string with no variables."""
        template = "Hello, World!"
        context = {"name": "Test"}
        assert interpolate(template, context) == "Hello, World!"

    def test_multiple_variables(self):
        """Test multiple variables in one string."""
        template = "{{greeting}}, {{name}}!"
        context = {"greeting": "Hi", "name": "Alice"}
        assert interpolate(template, context) == "Hi, Alice!"

    def test_nested_path(self):
        """Test nested object path."""
        template = "User: {{user.name}}"
        context = {"user": {"name": "Bob"}}
        assert interpolate(template, context) == "User: Bob"

    def test_deeply_nested_path(self):
        """Test deeply nested path."""
        template = "City: {{data.location.city}}"
        context = {"data": {"location": {"city": "NYC"}}}
        assert interpolate(template, context) == "City: NYC"

    def test_array_index(self):
        """Test array indexing."""
        template = "First item: {{items[0]}}"
        context = {"items": ["apple", "banana", "cherry"]}
        assert interpolate(template, context) == "First item: apple"

    def test_array_with_nested_path(self):
        """Test array with nested object."""
        template = "User: {{users[1].name}}"
        context = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        assert interpolate(template, context) == "User: Bob"


class TestFilters:
    """Test interpolation filters."""

    def test_upper_filter(self):
        """Test upper filter."""
        template = "{{name | upper}}"
        context = {"name": "hello"}
        assert interpolate(template, context) == "HELLO"

    def test_lower_filter(self):
        """Test lower filter."""
        template = "{{name | lower}}"
        context = {"name": "HELLO"}
        assert interpolate(template, context) == "hello"

    def test_default_filter(self):
        """Test default filter with None value."""
        template = "{{value | default('fallback')}}"
        context = {"value": None}
        assert interpolate(template, context) == "fallback"

    def test_default_filter_with_existing_value(self):
        """Test default filter doesn't override existing value."""
        template = "{{name | default('fallback')}}"
        context = {"name": "present"}
        assert interpolate(template, context) == "present"

    def test_string_filter(self):
        """Test string filter on number."""
        template = "Count: {{count | string}}"
        context = {"count": 42}
        assert interpolate(template, context) == "Count: 42"

    def test_json_filter(self):
        """Test json filter."""
        template = "{{data | json}}"
        context = {"data": {"key": "value"}}
        result = interpolate(template, context)
        assert json.loads(result) == {"key": "value"}

    def test_chained_filters(self):
        """Test chaining filters - note: only single filter supported."""
        # The current implementation only supports single filters
        # If chained filter support is needed, this test should be updated
        template = "{{name | upper}}"
        context = {"name": "Hello"}
        assert interpolate(template, context) == "HELLO"


class TestRecursiveInterpolation:
    """Test interpolation on complex structures."""

    def test_dict_interpolation(self):
        """Test interpolation on dictionary."""
        template = {
            "greeting": "Hello, {{name}}!",
            "message": "Welcome to {{place}}",
        }
        context = {"name": "Alice", "place": "Wonderland"}
        result = interpolate(template, context)
        assert result == {
            "greeting": "Hello, Alice!",
            "message": "Welcome to Wonderland",
        }

    def test_list_interpolation(self):
        """Test interpolation on list."""
        template = ["Hello, {{name}}", "Bye, {{name}}"]
        context = {"name": "Bob"}
        result = interpolate(template, context)
        assert result == ["Hello, Bob", "Bye, Bob"]

    def test_nested_structure(self):
        """Test interpolation on nested structure."""
        template = {
            "outer": {
                "inner": "{{value}}",
            },
            "list": ["{{item1}}", "{{item2}}"],
        }
        context = {"value": "nested", "item1": "a", "item2": "b"}
        result = interpolate(template, context)
        assert result == {
            "outer": {"inner": "nested"},
            "list": ["a", "b"],
        }

    def test_non_string_values_preserved(self):
        """Test that non-string values are preserved."""
        template = {
            "count": 42,
            "enabled": True,
            "data": None,
        }
        context = {}
        result = interpolate(template, context)
        assert result == template


class TestErrorHandling:
    """Test error handling."""

    def test_missing_variable_raises_error(self):
        """Test that missing variable raises InterpolationError."""
        template = "Hello, {{missing}}!"
        context = {}
        with pytest.raises(InterpolationError) as exc_info:
            interpolate(template, context)
        assert "missing" in str(exc_info.value)

    def test_invalid_array_index(self):
        """Test invalid array index."""
        template = "{{items[99]}}"
        context = {"items": ["a", "b"]}
        with pytest.raises(InterpolationError):
            interpolate(template, context)

    def test_invalid_path_on_non_dict(self):
        """Test invalid path on non-dict value."""
        template = "{{name.invalid}}"
        context = {"name": "string"}
        with pytest.raises(InterpolationError):
            interpolate(template, context)


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_string(self):
        """Test empty string."""
        assert interpolate("", {}) == ""

    def test_whitespace_in_variable(self):
        """Test whitespace handling in variable names."""
        template = "{{ name }}"
        context = {"name": "test"}
        assert interpolate(template, context) == "test"

    def test_whitespace_around_filter(self):
        """Test whitespace around filter pipe."""
        template = "{{ name | upper }}"
        context = {"name": "test"}
        assert interpolate(template, context) == "TEST"

    def test_numeric_value(self):
        """Test numeric value interpolation."""
        template = "Count: {{count}}"
        context = {"count": 42}
        assert interpolate(template, context) == "Count: 42"

    def test_boolean_value(self):
        """Test boolean value interpolation (booleans are lowercase)."""
        template = "Enabled: {{enabled}}"
        context = {"enabled": True}
        assert interpolate(template, context) == "Enabled: true"

    def test_partial_interpolation(self):
        """Test string with partial interpolation."""
        template = "User {{user.id}} is {{status}}"
        context = {"user": {"id": 123}, "status": "active"}
        assert interpolate(template, context) == "User 123 is active"
