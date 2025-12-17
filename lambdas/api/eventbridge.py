"""EventBridge rule management for cron triggers.

This module provides utilities to create, update, and delete
EventBridge rules when workflows with cron triggers are saved.
"""

from __future__ import annotations

import json
import os

import boto3
from aws_lambda_powertools import Logger

logger = Logger(child=True)

# AWS clients
events_client = boto3.client("events")

# Environment variables
ENV = os.environ.get("ENVIRONMENT", "dev")
CRON_HANDLER_ARN = os.environ.get("CRON_HANDLER_LAMBDA_ARN", "")


def get_rule_name(workflow_id: str) -> str:
    """Generate EventBridge rule name from workflow ID.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Rule name following naming convention
    """
    return f"automations-{ENV}-{workflow_id}-schedule"


def create_schedule_rule(workflow_id: str, schedule: str) -> None:
    """Create or update EventBridge rule for cron trigger.

    This is idempotent - calling it multiple times with the same
    workflow_id will update the existing rule.

    Args:
        workflow_id: Workflow identifier
        schedule: EventBridge schedule expression (cron or rate)

    Raises:
        ValueError: If CRON_HANDLER_LAMBDA_ARN is not configured
        ClientError: If EventBridge API call fails
    """
    if not CRON_HANDLER_ARN:
        logger.error("CRON_HANDLER_LAMBDA_ARN not configured")
        raise ValueError("Cron handler Lambda ARN not configured")

    rule_name = get_rule_name(workflow_id)

    logger.info(
        "Creating EventBridge rule",
        rule_name=rule_name,
        schedule=schedule,
        workflow_id=workflow_id,
    )

    # Create/update rule
    events_client.put_rule(
        Name=rule_name,
        ScheduleExpression=schedule,
        State="ENABLED",
        Description=f"Cron trigger for workflow {workflow_id}",
    )

    # Set target to cron handler Lambda
    # Use InputTransformer to include EventBridge time in the event
    events_client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "cron-handler",
                "Arn": CRON_HANDLER_ARN,
                "InputTransformer": {
                    "InputPathsMap": {
                        "time": "$.time",
                    },
                    "InputTemplate": json.dumps({
                        "workflow_id": workflow_id,
                        "source": "eventbridge-schedule",
                        "time": "<time>",
                    }).replace('"<time>"', '<time>'),  # InputTemplate uses <var> without quotes for strings
                },
            }
        ],
    )

    logger.info("EventBridge rule created/updated", rule_name=rule_name)


def delete_schedule_rule(workflow_id: str) -> None:
    """Delete EventBridge rule for workflow.

    This is idempotent - calling it for a non-existent rule
    will not raise an error.

    Args:
        workflow_id: Workflow identifier
    """
    rule_name = get_rule_name(workflow_id)

    logger.info(
        "Deleting EventBridge rule",
        rule_name=rule_name,
        workflow_id=workflow_id,
    )

    try:
        # Remove targets first (required before deleting rule)
        events_client.remove_targets(
            Rule=rule_name,
            Ids=["cron-handler"],
        )
    except events_client.exceptions.ResourceNotFoundException:
        logger.info("Rule not found, skipping target removal", rule_name=rule_name)
        return

    try:
        events_client.delete_rule(Name=rule_name)
        logger.info("EventBridge rule deleted", rule_name=rule_name)
    except events_client.exceptions.ResourceNotFoundException:
        logger.info("Rule already deleted", rule_name=rule_name)


def sync_workflow_rule(
    workflow_id: str,
    old_trigger: dict | None,
    new_trigger: dict | None,
) -> None:
    """Sync EventBridge rule based on workflow trigger changes.

    Handles all trigger change scenarios:
    - Non-cron to cron: Create rule
    - Cron to cron: Update rule (schedule may have changed)
    - Cron to non-cron: Delete rule
    - Non-cron to non-cron: No action

    Args:
        workflow_id: Workflow identifier
        old_trigger: Previous trigger configuration (None for new workflow)
        new_trigger: New trigger configuration (None for deleted workflow)
    """
    old_is_cron = (old_trigger or {}).get("type") == "cron"
    new_is_cron = (new_trigger or {}).get("type") == "cron"

    if new_is_cron:
        # Create or update rule
        schedule = (new_trigger or {}).get("config", {}).get("schedule", "")
        if schedule:
            create_schedule_rule(workflow_id, schedule)
        else:
            logger.warning(
                "Cron trigger missing schedule, skipping rule creation",
                workflow_id=workflow_id,
            )
    elif old_is_cron:
        # Changed away from cron, delete rule
        delete_schedule_rule(workflow_id)
