"""DynamoDB repository for Workflow and Execution operations.

This module provides a data access layer for the Workflows and Executions tables,
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
EXECUTIONS_TABLE_NAME = os.environ.get("EXECUTIONS_TABLE_NAME", "dev-Executions")

# Initialize DynamoDB resource
_dynamodb = boto3.resource("dynamodb")
_table: Table | None = None
_executions_table: Table | None = None


def get_table() -> Table:
    """Get the Workflows DynamoDB table resource (lazy initialization).

    Returns:
        DynamoDB Table resource
    """
    global _table
    if _table is None:
        _table = _dynamodb.Table(TABLE_NAME)
    return _table


def get_executions_table() -> Table:
    """Get the Executions DynamoDB table resource (lazy initialization).

    Returns:
        DynamoDB Table resource
    """
    global _executions_table
    if _executions_table is None:
        _executions_table = _dynamodb.Table(EXECUTIONS_TABLE_NAME)
    return _executions_table


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
        ProjectionExpression="workflow_id, #n, description, enabled, #t, steps, created_at, updated_at",
        ExpressionAttributeNames={
            "#n": "name",  # 'name' is a reserved word
            "#t": "trigger",  # 'trigger' is a reserved word
        },
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
            # Use aliases for ALL attributes to handle reserved words
            # (trigger, name, status, type, data, count are all reserved)
            alias = f"#{key}"
            update_parts.append(f"{alias} = :{key}")
            expression_values[f":{key}"] = value
            expression_names[alias] = key

    if not update_parts:
        # No updates to make, just return existing item
        return get_workflow(workflow_id)

    update_expression = "SET " + ", ".join(update_parts)

    try:
        response = table.update_item(
            Key={"workflow_id": workflow_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names,
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


# -----------------------------------------------------------------------------
# Execution Repository Functions
# -----------------------------------------------------------------------------


def list_executions(
    workflow_id: str,
    limit: int = 20,
    last_key: str | None = None,
) -> dict[str, Any]:
    """List executions for a workflow with pagination.

    Args:
        workflow_id: The workflow identifier
        limit: Maximum number of items to return (default 20)
        last_key: Last execution_id for pagination

    Returns:
        Dict with 'items' list and optional 'last_key' for pagination
    """
    table = get_executions_table()

    logger.info(
        "Querying executions",
        workflow_id=workflow_id,
        limit=limit,
        last_key=last_key,
    )

    # Build query parameters
    query_params: dict[str, Any] = {
        "KeyConditionExpression": "workflow_id = :wid",
        "ExpressionAttributeValues": {":wid": workflow_id},
        "Limit": limit,
        "ScanIndexForward": False,  # Most recent first
    }

    # Add pagination key if provided
    if last_key:
        query_params["ExclusiveStartKey"] = {
            "workflow_id": workflow_id,
            "execution_id": last_key,
        }

    response = table.query(**query_params)

    items = response.get("Items", [])
    logger.info("Found executions", count=len(items))

    result: dict[str, Any] = {"items": items}

    # Include pagination key if more results available
    if "LastEvaluatedKey" in response:
        result["last_key"] = response["LastEvaluatedKey"]["execution_id"]

    return result


def get_execution(workflow_id: str, execution_id: str) -> dict[str, Any] | None:
    """Get a single execution by ID.

    Args:
        workflow_id: The workflow identifier
        execution_id: The execution identifier

    Returns:
        Execution item if found, None otherwise
    """
    table = get_executions_table()

    logger.info(
        "Getting execution",
        workflow_id=workflow_id,
        execution_id=execution_id,
    )

    response = table.get_item(
        Key={
            "workflow_id": workflow_id,
            "execution_id": execution_id,
        }
    )
    item = response.get("Item")

    if item:
        logger.info("Execution found", execution_id=execution_id)
    else:
        logger.warning("Execution not found", execution_id=execution_id)

    return item
