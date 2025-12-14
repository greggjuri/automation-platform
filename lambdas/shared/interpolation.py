"""Variable interpolation utility for workflow execution.

Replaces {{path.to.value}} placeholders with actual values from context.
Supports nested paths, array indexing, and filters.
"""

from __future__ import annotations

import re
from typing import Any


class InterpolationError(Exception):
    """Raised when variable interpolation fails."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"Interpolation error for '{path}': {message}")


# Pattern to match {{variable}} or {{variable | filter}}
VARIABLE_PATTERN = re.compile(r"\{\{\s*([^}|]+?)(?:\s*\|\s*([^}]+?))?\s*\}\}")

# Pattern for array indexing like items[0]
ARRAY_INDEX_PATTERN = re.compile(r"^(.+?)\[(\d+)\]$")


def _resolve_path(context: dict, path: str) -> Any:
    """Resolve a dot-separated path to a value in context.

    Args:
        context: The context dictionary to search in
        path: Dot-separated path like "trigger.items[0].name"

    Returns:
        The value at the path

    Raises:
        InterpolationError: If path cannot be resolved
    """
    parts = path.strip().split(".")
    current = context

    for part in parts:
        if current is None:
            raise InterpolationError(path, f"Cannot access '{part}' on None")

        # Check for array indexing
        array_match = ARRAY_INDEX_PATTERN.match(part)
        if array_match:
            key, index = array_match.groups()
            index = int(index)

            # Get the array
            if isinstance(current, dict):
                if key not in current:
                    raise InterpolationError(path, f"Key '{key}' not found")
                current = current[key]
            else:
                raise InterpolationError(
                    path, f"Expected dict to access '{key}', got {type(current).__name__}"
                )

            # Access the index
            if not isinstance(current, (list, tuple)):
                raise InterpolationError(
                    path, f"Expected list for index [{index}], got {type(current).__name__}"
                )
            if index >= len(current):
                raise InterpolationError(
                    path, f"Index {index} out of range (length {len(current)})"
                )
            current = current[index]
        else:
            # Regular key access
            if isinstance(current, dict):
                if part not in current:
                    raise InterpolationError(path, f"Key '{part}' not found")
                current = current[part]
            elif isinstance(current, (list, tuple)):
                raise InterpolationError(
                    path, f"Cannot access key '{part}' on list"
                )
            else:
                raise InterpolationError(
                    path, f"Cannot access '{part}' on {type(current).__name__}"
                )

    return current


def _apply_filter(value: Any, filter_expr: str, path: str) -> Any:
    """Apply a filter to a value.

    Supported filters:
    - upper: Convert to uppercase
    - lower: Convert to lowercase
    - default('value'): Use default if None or missing
    - string: Convert to string
    - json: Keep as-is (for JSON serialization)

    Args:
        value: The value to filter
        filter_expr: Filter expression like "upper" or "default('N/A')"
        path: Original path for error messages

    Returns:
        Filtered value

    Raises:
        InterpolationError: If filter is unknown or fails
    """
    filter_name = filter_expr.strip()

    # Check for default filter with argument
    default_match = re.match(r"default\(['\"](.+?)['\"]\)", filter_name)
    if default_match:
        default_value = default_match.group(1)
        return default_value if value is None else value

    # Simple filters
    if filter_name == "upper":
        if not isinstance(value, str):
            raise InterpolationError(path, f"Filter 'upper' requires string, got {type(value).__name__}")
        return value.upper()

    if filter_name == "lower":
        if not isinstance(value, str):
            raise InterpolationError(path, f"Filter 'lower' requires string, got {type(value).__name__}")
        return value.lower()

    if filter_name == "string":
        return str(value) if value is not None else ""

    if filter_name == "json":
        return value

    raise InterpolationError(path, f"Unknown filter: {filter_name}")


def _interpolate_string(template: str, context: dict) -> str:
    """Interpolate variables in a string template.

    Args:
        template: String with {{variable}} placeholders
        context: Context dictionary with values

    Returns:
        String with placeholders replaced

    Raises:
        InterpolationError: If any variable cannot be resolved
    """

    def replace_match(match: re.Match) -> str:
        path = match.group(1)
        filter_expr = match.group(2)

        # Resolve the path
        value = _resolve_path(context, path)

        # Apply filter if present
        if filter_expr:
            value = _apply_filter(value, filter_expr, path)

        # Convert to string for interpolation
        if value is None:
            return ""
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (dict, list)):
            # For complex types in string context, use repr
            import json

            return json.dumps(value)
        return str(value)

    return VARIABLE_PATTERN.sub(replace_match, template)


def interpolate(template: str | dict | list, context: dict) -> str | dict | list:
    """Interpolate variables in a template.

    Replaces {{path.to.value}} with actual values from context.

    Supports:
    - Simple paths: {{trigger.title}}
    - Nested paths: {{steps.step_1.output.data}}
    - Array indexing: {{trigger.items[0].name}}
    - Filters: {{trigger.title | upper}}, {{value | default('N/A')}}

    Args:
        template: String, dict, or list containing {{variable}} placeholders
        context: Dictionary with structure:
            {
                "trigger": {...},
                "steps": {"step_id": {"output": {...}}},
                "secrets": {"name": "value"}
            }

    Returns:
        Template with all placeholders replaced

    Raises:
        InterpolationError: If any variable path cannot be resolved
    """
    if isinstance(template, str):
        return _interpolate_string(template, context)

    if isinstance(template, dict):
        return {
            key: interpolate(value, context)
            for key, value in template.items()
        }

    if isinstance(template, list):
        return [interpolate(item, context) for item in template]

    # For other types (int, float, bool, None), return as-is
    return template
