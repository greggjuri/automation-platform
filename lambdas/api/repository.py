"""DynamoDB repository for Workflow operations.

This module provides a data access layer for the Workflows table,
encapsulating all DynamoDB operations.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import boto3
from aws_lambda_powertools import Logger

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

logger = Logger(child=True)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

TABLE_NAME = os.environ.get("TABLE_NAME", "dev-Workflows")

# Initialize DynamoDB resource
_dynamodb = boto3.resource("dynamodb")
_table: Table | None = None


def get_table() -> Table:
    """Get the DynamoDB table resource (lazy initialization).

    Returns:
        DynamoDB Table resource
    """
    global _table
    if _table is None:
        _table = _dynamodb.Table(TABLE_NAME)
    return _table


# -----------------------------------------------------------------------------
# Repository Functions
# -----------------------------------------------------------------------------


def list_workflows() -> list[dict[str, Any]]:
    """List all workflows.

    Returns:
        List of workflow items

    Note:
        Uses scan which is fine for small datasets.
        For large datasets, implement pagination with GSI.
    """
    table = get_table()

    logger.info("Scanning workflows table")

    response = table.scan(
        ProjectionExpression="workflow_id, #n, description, enabled, created_at, updated_at",
        ExpressionAttributeNames={"#n": "name"},  # 'name' is a reserved word
    )

    items = response.get("Items", [])
    logger.info("Found workflows", count=len(items))

    return items


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    """Get a single workflow by ID.

    Args:
        workflow_id: The workflow identifier

    Returns:
        Workflow item if found, None otherwise
    """
    table = get_table()

    logger.info("Getting workflow", workflow_id=workflow_id)

    response = table.get_item(Key={"workflow_id": workflow_id})
    item = response.get("Item")

    if item:
        logger.info("Workflow found", workflow_id=workflow_id)
    else:
        logger.warning("Workflow not found", workflow_id=workflow_id)

    return item


def create_workflow(item: dict[str, Any]) -> dict[str, Any]:
    """Create a new workflow.

    Args:
        item: Complete workflow item including workflow_id and timestamps

    Returns:
        The created workflow item
    """
    table = get_table()

    logger.info("Creating workflow", workflow_id=item.get("workflow_id"))

    table.put_item(Item=item)

    logger.info("Workflow created", workflow_id=item.get("workflow_id"))

    return item


def update_workflow(workflow_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update an existing workflow.

    Args:
        workflow_id: The workflow identifier
        updates: Dictionary of fields to update (only non-None values)

    Returns:
        Updated workflow item, or None if workflow doesn't exist
    """
    table = get_table()

    logger.info("Updating workflow", workflow_id=workflow_id, fields=list(updates.keys()))

    # Build update expression dynamically
    update_parts = []
    expression_values = {}
    expression_names = {}

    for key, value in updates.items():
        if value is not None:
            # Handle reserved words
            if key == "name":
                update_parts.append("#n = :name")
                expression_values[":name"] = value
                expression_names["#n"] = "name"
            else:
                update_parts.append(f"{key} = :{key}")
                expression_values[f":{key}"] = value

    if not update_parts:
        # No updates to make, just return existing item
        return get_workflow(workflow_id)

    update_expression = "SET " + ", ".join(update_parts)

    try:
        response = table.update_item(
            Key={"workflow_id": workflow_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names if expression_names else None,
            ConditionExpression="attribute_exists(workflow_id)",
            ReturnValues="ALL_NEW",
        )

        updated_item = response.get("Attributes", {})
        logger.info("Workflow updated", workflow_id=workflow_id)

        return updated_item

    except table.meta.client.exceptions.ConditionalCheckFailedException:
        logger.warning("Workflow not found for update", workflow_id=workflow_id)
        return None


def delete_workflow(workflow_id: str) -> bool:
    """Delete a workflow.

    Args:
        workflow_id: The workflow identifier

    Returns:
        True if deleted, False if workflow didn't exist
    """
    table = get_table()

    logger.info("Deleting workflow", workflow_id=workflow_id)

    try:
        table.delete_item(
            Key={"workflow_id": workflow_id},
            ConditionExpression="attribute_exists(workflow_id)",
        )

        logger.info("Workflow deleted", workflow_id=workflow_id)
        return True

    except table.meta.client.exceptions.ConditionalCheckFailedException:
        logger.warning("Workflow not found for delete", workflow_id=workflow_id)
        return False
